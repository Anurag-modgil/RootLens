import logging
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import HDBSCAN
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Log, Cluster, Incident
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("rootlens.clustering")

class ClusteringService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.client = self.vector_store._client
        self.collection_name = settings.qdrant_collection

    def run_clustering(self, db: Session):
        logger.info("Starting HDBSCAN log clustering job...")

        # 1. Retrieve all points with vectors from Qdrant
        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_vectors=True,
                with_payload=True
            )
            points = scroll_result[0]
        except Exception as e:
            logger.error(f"Failed to scroll points from Qdrant: {str(e)}")
            return

        if not points or len(points) < 2:
            logger.info("Not enough logs in Qdrant (minimum 2 required) to perform clustering. Skipping.")
            return

        # 2. Extract vectors and log IDs
        log_ids = []
        vectors = []
        point_map = {}
        for p in points:
            log_ids.append(p.id)
            vectors.append(p.vector)
            point_map[p.id] = p

        # 3. Compile and L2-normalize vector matrix
        X = np.array(vectors)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        X_normalized = X / (norms + 1e-12)

        # 4. Fit HDBSCAN model (Euclidean distance on L2 normalized vectors is Cosine distance)
        try:
            hdb = HDBSCAN(min_cluster_size=2, min_samples=1, metric='euclidean')
            labels = hdb.fit_predict(X_normalized)
        except Exception as e:
            logger.error(f"HDBSCAN fitting failed: {str(e)}")
            return

        # Group log IDs by cluster label
        groups: Dict[int, List[int]] = {}
        for log_id, label in zip(log_ids, labels):
            groups.setdefault(int(label), []).append(log_id)

        logger.info(f"Clustering completed. Found groups: {list(groups.keys())}")

        # 5. Process each group and sync relational database + Qdrant payloads
        for label, group_log_ids in groups.items():
            if label == -1:
                # Handle noise logs
                logger.info(f"Processing {len(group_log_ids)} logs labeled as noise (-1).")
                
                # Update SQL DB: set cluster_id to Null
                db.query(Log).filter(Log.id.in_(group_log_ids)).update(
                    {Log.cluster_id: None},
                    synchronize_session=False
                )
                db.commit()

                # Update Qdrant payloads: clear cluster_id and incident_id
                try:
                    self.client.set_payload(
                        collection_name=self.collection_name,
                        payload={"cluster_id": None, "incident_id": None},
                        points=group_log_ids
                    )
                except Exception as e:
                    logger.error(f"Failed to clear Qdrant payload for noise logs: {str(e)}")
            else:
                # Handle clustered logs
                logger.info(f"Processing Cluster Group {label} containing logs: {group_log_ids}")

                # Fetch corresponding Log model instances from database
                db_logs = db.query(Log).filter(Log.id.in_(group_log_ids)).all()
                if not db_logs:
                    continue

                # Find if any logs in this group already have a cluster assigned
                existing_cluster_ids = [l.cluster_id for l in db_logs if l.cluster_id is not None]
                
                cluster_id = None
                if existing_cluster_ids:
                    # Use the most common cluster ID as the anchor
                    cluster_id = max(set(existing_cluster_ids), key=existing_cluster_ids.count)
                    logger.info(f"Merged group with existing Database Cluster ID: {cluster_id}")
                
                # Retrieve or create cluster
                db_cluster = None
                if cluster_id is not None:
                    db_cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()

                if db_cluster is None:
                    # Create new Cluster
                    # Generate dynamic name based on service_name & log_level distribution
                    services = [l.service_name for l in db_logs]
                    levels = [l.log_level for l in db_logs]
                    most_common_svc = max(set(services), key=services.count) if services else "unknown"
                    most_common_lvl = max(set(levels), key=levels.count) if levels else "INFO"
                    
                    cluster_name = f"Cluster: {most_common_svc} - {most_common_lvl}"
                    
                    db_cluster = Cluster(
                        name=cluster_name,
                        summary=f"Auto-grouped cluster of {len(group_log_ids)} similar logs."
                    )
                    db.add(db_cluster)
                    db.commit()
                    db.refresh(db_cluster)
                    cluster_id = db_cluster.id
                    logger.info(f"Created new Database Cluster: '{cluster_name}' (ID: {cluster_id})")

                # Ensure there is an Incident associated with this cluster if it represents errors
                incident_id = db_cluster.incident_id
                if incident_id is None:
                    # If it contains high severity logs, auto-create an incident
                    contains_errors = any(l.log_level in ["ERROR", "CRITICAL", "FATAL"] for l in db_logs)
                    if contains_errors:
                        db_incident = Incident(
                            title=f"Incident for {db_cluster.name}",
                            description=f"Automated incident generated for log cluster containing error logs.",
                            status="OPEN",
                            severity="CRITICAL" if any(l.log_level == "CRITICAL" for l in db_logs) else "HIGH"
                        )
                        db.add(db_incident)
                        db.commit()
                        db.refresh(db_incident)
                        
                        db_cluster.incident_id = db_incident.id
                        db.commit()
                        incident_id = db_incident.id
                        logger.info(f"Auto-generated and linked Incident ID {incident_id} for Cluster ID {cluster_id}")

                # Update SQL Logs with new cluster_id
                db.query(Log).filter(Log.id.in_(group_log_ids)).update(
                    {Log.cluster_id: cluster_id},
                    synchronize_session=False
                )
                db.commit()

                # Sync Qdrant payloads with the resolved cluster_id and incident_id
                try:
                    self.client.set_payload(
                        collection_name=self.collection_name,
                        payload={
                            "cluster_id": cluster_id,
                            "incident_id": incident_id
                        },
                        points=group_log_ids
                    )
                    logger.info(f"Synchronized Qdrant payloads for Cluster Group {label} (points {group_log_ids}).")
                except Exception as e:
                    logger.error(f"Failed to sync Qdrant payloads for group {group_log_ids}: {str(e)}")

        logger.info("Log clustering job finished successfully.")
