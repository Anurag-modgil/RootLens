import logging
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import Log, Cluster, Incident
from app.services.embeddings import LogEmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.clustering import ClusteringService

# Setup logger to see details
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def test_clustering_engine():
    print("--- Starting Clustering Engine Test ---")
    
    # 1. Setup fresh relational DB
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    # Clean previous data to ensure test isolation
    db.query(Log).delete()
    db.query(Cluster).delete()
    db.query(Incident).delete()
    db.commit()

    try:
        # 2. Setup Services
        embedding_service = LogEmbeddingService()
        vector_store = VectorStoreService()
        clustering_service = ClusteringService()

        # Mock logs dataset
        mock_logs = [
            # Group 1: Database connection errors (Expect to form Cluster A)
            {"msg": "Fatal: pg connection timeout after 5000ms.", "svc": "auth-service", "level": "ERROR"},
            {"msg": "Could not acquire DB connection from pool.", "svc": "billing-service", "level": "CRITICAL"},
            {"msg": "Database connection pool exhausted, transaction aborted.", "svc": "payment-gateway", "level": "ERROR"},
            
            # Group 2: Disk space errors (Expect to form Cluster B)
            {"msg": "No space left on device: writing to /var/log/app failed.", "svc": "file-service", "level": "ERROR"},
            {"msg": "Failed to write buffer to disk, local storage full.", "svc": "file-service", "level": "ERROR"},
            {"msg": "Storage threshold exceeded: disk capacity at 99%.", "svc": "system-monitor", "level": "WARNING"},
            
            # Group 3: Unrelated noise (Expect to be labeled as noise / -1)
            {"msg": "User user_58932 successfully logged out.", "svc": "session-manager", "level": "INFO"}
        ]

        print("\nIngesting mock logs to database and Qdrant...")
        for entry in mock_logs:
            # Create in SQL DB
            db_log = Log(
                timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                service_name=entry["svc"],
                log_level=entry["level"],
                message=entry["msg"]
            )
            db.add(db_log)
            db.commit()
            db.refresh(db_log)

            # Generate embedding
            vec = embedding_service.get_embedding(entry["msg"])

            # Index in Qdrant
            payload = {
                "log_id": db_log.id,
                "service_name": db_log.service_name,
                "log_level": db_log.log_level,
                "timestamp": db_log.timestamp.isoformat(),
                "message": db_log.message,
                "cluster_id": None,
                "incident_id": None
            }
            vector_store.upsert_log(log_id=db_log.id, vector=vec, payload=payload)

        # 3. Run Clustering Service
        print("\nExecuting HDBSCAN clustering job...")
        clustering_service.run_clustering(db)

        # 4. Verify SQL Database States
        print("\nVerifying SQL Database updates...")
        
        # Check clusters
        db_clusters = db.query(Cluster).all()
        print(f"Total Clusters created: {len(db_clusters)}")
        for c in db_clusters:
            print(f"- Cluster ID: {c.id}, Name: '{c.name}', Linked Incident: {c.incident_id}")
        
        # We expect exactly 2 clusters (DB errors and Disk errors)
        assert len(db_clusters) == 2, f"Expected 2 clusters, got {len(db_clusters)}"

        # Check incidents
        db_incidents = db.query(Incident).all()
        print(f"Total Incidents created: {len(db_incidents)}")
        for inc in db_incidents:
            print(f"- Incident ID: {inc.id}, Title: '{inc.title}', Severity: {inc.severity}")
        
        # We expect 2 incidents created automatically for the 2 error-prone clusters
        assert len(db_incidents) == 2, f"Expected 2 incidents, got {len(db_incidents)}"

        # Verify Logs assignments
        db_logs_retrieved = db.query(Log).order_by(Log.id).all()
        print("\nLog Database assignments:")
        for log in db_logs_retrieved:
            print(f"- [Log ID: {log.id}] Cluster ID: {log.cluster_id} -> '{log.message}'")

        # First 3 logs should share same cluster ID
        assert db_logs_retrieved[0].cluster_id == db_logs_retrieved[1].cluster_id == db_logs_retrieved[2].cluster_id
        assert db_logs_retrieved[0].cluster_id is not None
        
        # Middle 3 logs should share same cluster ID, but different from first group
        assert db_logs_retrieved[3].cluster_id == db_logs_retrieved[4].cluster_id == db_logs_retrieved[5].cluster_id
        assert db_logs_retrieved[3].cluster_id is not None
        assert db_logs_retrieved[3].cluster_id != db_logs_retrieved[0].cluster_id

        # The last log (noise) should have cluster_id = None
        assert db_logs_retrieved[6].cluster_id is None
        print("SQL Log cluster linkages verified!")

        # 5. Verify Qdrant payload synchronization
        print("\nVerifying Qdrant vector store synchronization...")
        scroll_result = vector_store._client.scroll(
            collection_name=vector_store.collection_name,
            limit=100,
            with_vectors=False,
            with_payload=True
        )
        qdrant_points = scroll_result[0]
        
        # Map Qdrant points by ID
        qp_map = {p.id: p.payload for p in qdrant_points}
        
        # Verify log ID 1 and 2 payload matches SQLite DB
        assert qp_map[1]["cluster_id"] == db_logs_retrieved[0].cluster_id
        assert qp_map[1]["incident_id"] is not None
        
        # Verify log ID 7 payload matches SQLite DB (Noise log - should have None)
        assert qp_map[7]["cluster_id"] is None
        assert qp_map[7]["incident_id"] is None
        print("Qdrant payload metadata synchronizations verified successfully!")

        print("\n--- All Clustering Engine Tests Passed! ---")

    except Exception as e:
        print(f"Clustering Engine test failed: {e}")
        db.rollback()
        raise e
    finally:
        # Clean up database
        print("\nCleaning database...")
        db.query(Log).delete()
        db.query(Cluster).delete()
        db.query(Incident).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    test_clustering_engine()
