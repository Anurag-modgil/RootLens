import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import Log
from app.services.vector_store import VectorStoreService
from app.services.embeddings import LogEmbeddingService

def test_async_ingestion():
    print("--- Starting Async Log Ingestion Test (TestClient) ---")
    
    # 1. Clean and setup relational DB
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    db.query(Log).delete()
    db.commit()

    # Create the test client
    client = TestClient(app)

    # 2. Make request payload
    payload = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "service_name": "async-test-service",
        "log_level": "WARNING",
        "message": "Out of memory warning: system resource threshold breached."
    }

    try:
        # Send HTTP POST using TestClient (runs in-process)
        response = client.post("/api/v1/logs", json=payload)
        
        print(f"Ingestion response code: {response.status_code}")
        res_json = response.json()
        print(f"Ingestion message: {res_json['message']}")
        
        assert response.status_code == 201
        assert res_json["status"] == "success"
        
        log_id = res_json["log"]["id"]
        print(f"Log successfully saved in SQLite database with ID: {log_id}")

        # 3. Verify task indexed log in Qdrant
        # Since CELERY_ALWAYS_EAGER=True by default, the task completed synchronously
        # within the request thread inside this same process!
        vector_store = VectorStoreService()
        embedding_service = LogEmbeddingService()
        
        query_vec = embedding_service.get_embedding(payload["message"])
        hits = vector_store.search_similar_logs(query_vec, limit=5)
        
        print("\nSearching similar indexed logs in Qdrant:")
        found = False
        for hit in hits:
            print(f"- Found Log ID: {hit['log_id']}, Score: {hit['score']:.4f}, Message: '{hit['payload']['message']}'")
            if hit["log_id"] == log_id:
                found = True
        
        assert found, f"Log ID {log_id} was not found indexed in Qdrant! Asynchronous processing failed."
        print("\nAsync task verification completed successfully! Log was properly indexed in Qdrant.")
        print("--- All Async Log Processing Tests Passed! ---")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        raise e
    finally:
        # Clean up database
        db.query(Log).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    test_async_ingestion()
