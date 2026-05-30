import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from app.models import Incident

logger = logging.getLogger("rootlens.vector_store")

class VectorStoreService:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorStoreService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure client is initialized only once
        if self._client is None:
            self.collection_name = settings.qdrant_collection
            logger.info(f"Initializing Qdrant client at '{settings.qdrant_url}'...")
            try:
                if settings.qdrant_url == ":memory:":
                    self._client = QdrantClient(location=":memory:")
                elif (settings.qdrant_url.startswith("http://") or 
                      settings.qdrant_url.startswith("https://") or 
                      settings.qdrant_url.startswith("grpc://")):
                    self._client = QdrantClient(url=settings.qdrant_url)
                else:
                    # Treat as local directory storage path (e.g., "qdrant_storage")
                    self._client = QdrantClient(path=settings.qdrant_url)
                
                self._ensure_collection()
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant client: {str(e)}")
                raise RuntimeError(f"Qdrant service initialization failure: {str(e)}")

    def _ensure_collection(self):
        """
        Check if the collection exists, and create it if not.
        """
        try:
            exists = self._client.collection_exists(self.collection_name)
            if not exists:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' with 384 dimensions...")
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Collection '{self.collection_name}' created successfully.")
            else:
                logger.info(f"Qdrant collection '{self.collection_name}' already exists.")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {str(e)}")
            raise

    def upsert_log(self, log_id: int, vector: List[float], payload: Dict[str, Any]):
        """
        Upsert a log embedding and payload metadata into Qdrant.
        """
        try:
            point = PointStruct(
                id=log_id,
                vector=vector,
                payload=payload
            )
            self._client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.debug(f"Successfully upserted log ID {log_id} into Qdrant.")
        except Exception as e:
            logger.error(f"Failed to upsert log ID {log_id} in Qdrant: {str(e)}")
            raise RuntimeError(f"Qdrant upsert failed: {str(e)}")

    def search_similar_logs(self, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search over log embeddings.
        Returns a list of search hits with payload and score.
        """
        try:
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit
            )
            hits = []
            for hit in results.points:
                hits.append({
                    "log_id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                })
            return hits
        except Exception as e:
            logger.error(f"Qdrant query_points failed: {str(e)}")
            raise RuntimeError(f"Qdrant query_points failed: {str(e)}")

    def search_similar_incidents(self, db: Session, vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search similar logs, resolve unique linked incidents, and return the top 10 unique incidents
        sorted by highest log similarity score.
        """
        # Fetch 5x the limit to account for duplicate incidents in the logs matching list
        search_limit = limit * 5
        hits = self.search_similar_logs(vector, limit=search_limit)

        incident_groups: Dict[int, Dict[str, Any]] = {}

        for hit in hits:
            payload = hit["payload"]
            incident_id = payload.get("incident_id")
            
            if incident_id is not None:
                if incident_id not in incident_groups:
                    # Query the SQL database for the incident details
                    incident = db.query(Incident).filter(Incident.id == incident_id).first()
                    if incident:
                        incident_groups[incident_id] = {
                            "incident": incident,
                            "max_score": hit["score"],
                            "matched_logs": []
                        }
                
                # Append matching log context if the incident exists
                if incident_id in incident_groups:
                    incident_groups[incident_id]["matched_logs"].append({
                        "log_id": hit["log_id"],
                        "score": hit["score"],
                        "message": payload.get("message", "")
                    })
                    # Keep track of the highest score for this incident group
                    if hit["score"] > incident_groups[incident_id]["max_score"]:
                        incident_groups[incident_id]["max_score"] = hit["score"]

        # Sort resolved unique incidents by their max similarity score in descending order
        sorted_incidents = sorted(
            incident_groups.values(),
            key=lambda x: x["max_score"],
            reverse=True
        )

        return sorted_incidents[:limit]
