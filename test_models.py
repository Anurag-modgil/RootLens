from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Incident, Cluster, Log
import datetime

def test_relationships():
    db: Session = SessionLocal()
    try:
        # 1. Create an incident
        incident = Incident(
            title="Database Connection Issue",
            description="Database pool exhausted, causing multiple timeout errors.",
            status="OPEN",
            severity="CRITICAL"
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        print(f"Created Incident ID: {incident.id}, Title: {incident.title}")

        # 2. Create a cluster linked to the incident
        cluster = Cluster(
            name="DB Timeout Group",
            summary="Logs indicating PostgreSQL connection timeouts.",
            incident_id=incident.id
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        print(f"Created Cluster ID: {cluster.id}, Name: {cluster.name}, Linked to Incident: {cluster.incident_id}")

        # 3. Create a log linked to the cluster
        log = Log(
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            service_name="payment-service",
            log_level="ERROR",
            message="Connection timeout while fetching user records from DB.",
            cluster_id=cluster.id
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        print(f"Created Log ID: {log.id}, Linked to Cluster: {log.cluster_id}")

        # 4. Verify relationships
        db.refresh(incident)
        assert len(incident.clusters) == 1
        assert incident.clusters[0].id == cluster.id
        print("Verified relationship: Incident -> Cluster (One-to-Many)")

        db.refresh(cluster)
        assert len(cluster.logs) == 1
        assert cluster.logs[0].id == log.id
        assert cluster.incident.id == incident.id
        print("Verified relationships: Cluster -> Log (One-to-Many) and Cluster -> Incident (Many-to-One)")

        assert log.cluster.id == cluster.id
        print("Verified relationship: Log -> Cluster (Many-to-One)")

        # 5. Test CASCADE delete (SET NULL) on incident deletion
        print("Deleting Incident...")
        db.delete(incident)
        db.commit()

        # The cluster should still exist, but incident_id should be None
        db.refresh(cluster)
        assert cluster.incident_id is None
        print("Verified SET NULL cascade: Cluster incident_id is now None.")

        # Clean up database
        print("Cleaning up...")
        db.delete(cluster)
        db.delete(log)
        db.commit()
        print("Database cleaned up successfully.")
        print("All relationship tests passed!")

    except Exception as e:
        print(f"Test failed with error: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_relationships()
