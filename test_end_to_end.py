import logging
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import Log, Cluster, Incident
from app.services.detection import IncidentDetectionEngine
from app.services.rag import RAGService
from app.services.rca import RootCauseAnalysisEngine
from app.services.remediation import RemediationAgent
from app.services.executor import SafeCommandExecutor

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def test_end_to_end():
    print("--- Starting End-to-End Self-Healing System Integration Test ---")
    
    # 1. Setup relational database
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    # Clean database
    db.query(Log).delete()
    db.query(Cluster).delete()
    db.query(Incident).delete()
    db.commit()

    try:
        # 2. Initialize RAG KB and add historical resolution
        print("\n=== STEP 1: Populating RAG Knowledge Base ===")
        rag_service = RAGService()
        
        # Add a historical solution that matches our simulated database failure
        rag_service.add_solution(
            title="Database Connection Pool Exhaustion on payment-gateway",
            description="Slow transactions caused database thread pool exhaustion.",
            solution="echo 'Restarting payment-gateway cache and connections'" # allowlisted safe command
        )

        # 3. Ingest log spike (5 ERROR logs within 1 minute from payment-gateway)
        print("\n=== STEP 2: Simulating Error Log Spike Ingestion ===")
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        
        for i in range(5):
            db_log = Log(
                timestamp=now - datetime.timedelta(seconds=i*10),
                service_name="payment-gateway",
                log_level="ERROR",
                message=f"Timeout error tx_9832{i}: Failed to acquire connection from database pool."
            )
            db.add(db_log)
        db.commit()
        print("Ingested 5 ERROR logs from payment-gateway.")

        # 4. Trigger Incident Detection Engine
        print("\n=== STEP 3: Running Incident Detection ===")
        detection_engine = IncidentDetectionEngine()
        incidents = detection_engine.run_detection(db)
        
        assert len(incidents) == 1, f"Expected 1 incident, detected {len(incidents)}"
        incident = incidents[0]
        print(f"Detected Incident ID: {incident.id}")
        print(f"Title: '{incident.title}'")
        print(f"Severity: {incident.severity}")
        assert incident.severity == "HIGH", f"Expected HIGH severity, got {incident.severity}"
        assert incident.status == "OPEN"

        # 5. Retrieve Solutions using RAG Search
        print("\n=== STEP 4: Querying RAG Knowledge Base ===")
        query_text = f"Title: {incident.title}\nDescription: {incident.description}"
        hits = rag_service.search_solutions(query_text, limit=1)
        
        assert len(hits) > 0, "No historical resolutions matched."
        print(f"RAG Top Match: '{hits[0]['title']}'")
        print(f"Proposed Solution: '{hits[0]['solution']}'")

        # 6. Run Root Cause Analysis (RCA) Engine
        print("\n=== STEP 5: Executing Root Cause Analysis (RCA) ===")
        rca_engine = RootCauseAnalysisEngine()
        
        # We query the database to fetch the logs that triggered the incident
        logs = db.query(Log).filter(Log.service_name == "payment-gateway").all()
        service_metadata = {
            "environment": "production",
            "active_version": "v2.1.4",
            "db_connections_limit": 100
        }
        
        rca_output = rca_engine.analyze_incident(
            incident=incident,
            logs=logs,
            service_metadata=service_metadata,
            historical_resolutions=hits
        )
        
        # Override fix with allowlisted RAG match if mock model ran
        if rca_engine.client is None:
            rca_output["recommended_fix"] = hits[0]["solution"]

        print("RCA Output:")
        print(f"  Root Cause: {rca_output['root_cause']}")
        print(f"  Confidence Score: {rca_output['confidence_score']:.2f}")
        print(f"  Impact: {rca_output['impact']}")
        print(f"  Recommended Fix: '{rca_output['recommended_fix']}'")

        # 7. Run Remediation Agent: Propose action
        print("\n=== STEP 6: Proposing Remediation Plan ===")
        remediation_agent = RemediationAgent()
        incident = remediation_agent.propose_remediation(db, incident, rca_output)
        
        assert incident.remediation_status == "PENDING_APPROVAL"
        assert incident.remediation_action == rca_output["recommended_fix"]
        print(f"Remediation action proposed and set to PENDING_APPROVAL: '{incident.remediation_action}'")

        # 8. Approve and Execute Remediation (Allowlisted command)
        print("\n=== STEP 7: Approving and Executing Allowed Remediation ===")
        success = remediation_agent.execute_approved_remediation(db, incident.id)
        
        assert success, "Execution failed but should have succeeded."
        db.refresh(incident)
        assert incident.remediation_status == "SUCCESS"
        assert incident.status == "RESOLVED"
        print(f"Execution Succeeded! Incident status updated to: {incident.status} (Remediation: {incident.remediation_status})")

        # 9. Test Security Block on Safe Command Executor
        print("\n=== STEP 8: Testing Command Executor Security Allowlist Block ===")
        executor = SafeCommandExecutor()
        
        # Unallowlisted command
        malicious_command = "rm -rf /Users/anurag/Desktop/RootLens"
        res_blocked = executor.execute_command(malicious_command)
        
        assert res_blocked["status"] == "blocked"
        print(f"Command: '{malicious_command}' -> Status: {res_blocked['status']} (Blocked successfully)")
        print(f"Security Alert Message: {res_blocked['error']}")

        print("\n--- All End-to-End Self-Healing System Integration Tests Passed! ---")

    except Exception as e:
        print(f"E2E Integration Test failed: {e}")
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
    test_end_to_end()
