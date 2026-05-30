import logging
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import Log, Cluster, Incident
from app.services.embeddings import LogEmbeddingService
from app.services.vector_store import VectorStoreService

# Setup logger to see details
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def test_qdrant_integration():
    print("--- Starting Qdrant Integration Test ---")
    
    # 1. Clean and setup relational DB
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

        # 3. Create mock database entities
        # Incident 1: Database Outage
        inc1 = Incident(title="DB Connectivity Outage", description="PostgreSQL pool exhausted.", status="OPEN", severity="CRITICAL")
        db.add(inc1)
        db.commit()
        db.refresh(inc1)

        # Incident 2: Disk Exhaustion
        inc2 = Incident(title="Disk Space Warning", description="App server storage filled up.", status="OPEN", severity="HIGH")
        db.add(inc2)
        db.commit()
        db.refresh(inc2)

        # Cluster 1 (linked to DB Outage)
        c1 = Cluster(name="DB Timeout Cluster", summary="Connection time outs on pg pool.", incident_id=inc1.id)
        db.add(c1)
        db.commit()
        db.refresh(c1)

        # Cluster 2 (linked to Disk Exhaustion)
        c2 = Cluster(name="Disk Space Cluster", summary="Writes failing due to full disk device.", incident_id=inc2.id)
        db.add(c2)
        db.commit()
        db.refresh(c2)

        # Mock logs
        log_data = [
            # DB logs (linked to Cluster 1 / Incident 1)
            {"msg": "Fatal: pg connection timeout after 5000ms.", "cluster": c1, "inc": inc1, "svc": "auth-service", "level": "ERROR"},
            {"msg": "Could not acquire DB connection from pool.", "cluster": c1, "inc": inc1, "svc": "billing-service", "level": "CRITICAL"},
            
            # Disk logs (linked to Cluster 2 / Incident 2)
            {"msg": "No space left on device: writing to /var/log/app failed.", "cluster": c2, "inc": inc2, "svc": "file-service", "level": "ERROR"},
            {"msg": "Failed to write buffer to disk, local storage full.", "cluster": c2, "inc": inc2, "svc": "file-service", "level": "ERROR"}
        ]

        # 4. Generate embeddings and populate DB + Qdrant
        print("\nIndexing logs into SQL and Qdrant...")
        for entry in log_data:
            # Save to SQL database
            db_log = Log(
                timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                service_name=entry["svc"],
                log_level=entry["level"],
                message=entry["msg"],
                cluster_id=entry["cluster"].id
            )
            db.add(db_log)
            db.commit()
            db.refresh(db_log)

            # Get embedding vector
            vec = embedding_service.get_embedding(entry["msg"])

            # Save in Qdrant Vector Store
            payload = {
                "log_id": db_log.id,
                "service_name": db_log.service_name,
                "log_level": db_log.log_level,
                "timestamp": db_log.timestamp.isoformat(),
                "message": db_log.message,
                "cluster_id": entry["cluster"].id,
                "incident_id": entry["inc"].id
            }
            vector_store.upsert_log(log_id=db_log.id, vector=vec, payload=payload)
            print(f"Indexed log: '{entry['msg']}' -> Qdrant Point ID: {db_log.id}")

        # 5. Search test 1: DB related query
        query_msg = "Database failure: connection refused by remote host."
        query_vec = embedding_service.get_embedding(query_msg)

        print(f"\nQuerying: '{query_msg}'")
        print("\nSimilar Logs:")
        similar_logs = vector_store.search_similar_logs(query_vec, limit=5)
        for hit in similar_logs:
            print(f"- Log ID: {hit['log_id']}, Score: {hit['score']:.4f}, Msg: '{hit['payload']['message']}'")
        
        assert len(similar_logs) > 0
        # The top match should be a DB-related log
        assert "DB" in similar_logs[0]["payload"]["message"] or "connection" in similar_logs[0]["payload"]["message"]

        # 6. Search test 2: Resolve Similar Incidents (Top 10)
        print("\nResolving similar incidents...")
        incidents_resolved = vector_store.search_similar_incidents(db, query_vec, limit=10)
        
        for idx, result in enumerate(incidents_resolved):
            inc = result["incident"]
            print(f"{idx+1}. Incident ID: {inc.id}, Title: '{inc.title}', Max Similarity Score: {result['max_score']:.4f}")
            print(f"   Matched logs in this incident:")
            for m_log in result["matched_logs"]:
                print(f"     * [Log ID: {m_log['log_id']}] Similarity: {m_log['score']:.4f} -> '{m_log['message']}'")

        assert len(incidents_resolved) > 0
        # The first resolved incident should be the DB Outage because we searched a DB failure message
        assert incidents_resolved[0]["incident"].id == inc1.id
        print("\nIncident resolution and ordering verified successfully!")

        print("\n--- All Qdrant Integration Tests Passed! ---")

    except Exception as e:
        print(f"Qdrant integration test failed: {e}")
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
    test_qdrant_integration()
