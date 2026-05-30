import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Log
from app.services.embeddings import LogEmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("rootlens.tasks")

@celery_app.task(name="app.tasks.process_log_embedding_task")
def process_log_embedding_task(log_id: int):
    logger.info(f"Processing asynchronous embedding task for Log ID: {log_id}")
    
    # 1. Setup services
    embedding_service = LogEmbeddingService()
    vector_store = VectorStoreService()
    
    # 2. Open a database session
    db = SessionLocal()
    try:
        # Fetch log from database
        log_entry = db.query(Log).filter(Log.id == log_id).first()
        if not log_entry:
            logger.error(f"Log ID {log_id} not found in database. Aborting task.")
            return False

        # 3. Generate embedding vector
        logger.info(f"Generating embedding for Log ID {log_id}...")
        vector = embedding_service.get_embedding(log_entry.message)

        # 4. Resolve the cluster's incident if any
        incident_id = None
        if log_entry.cluster and log_entry.cluster.incident_id:
            incident_id = log_entry.cluster.incident_id

        # 5. Populate payload metadata
        payload = {
            "log_id": log_entry.id,
            "service_name": log_entry.service_name,
            "log_level": log_entry.log_level,
            "timestamp": log_entry.timestamp.isoformat(),
            "message": log_entry.message,
            "cluster_id": log_entry.cluster_id,
            "incident_id": incident_id
        }

        # 6. Index embedding & payload in Qdrant
        logger.info(f"Indexing Log ID {log_id} in Qdrant vector database...")
        vector_store.upsert_log(
            log_id=log_entry.id,
            vector=vector,
            payload=payload
        )
        logger.info(f"Successfully processed Log ID {log_id}.")
        return True

    except Exception as e:
        logger.error(f"Failed to process embedding for Log ID {log_id}: {str(e)}")
        raise e
    finally:
        db.close()
