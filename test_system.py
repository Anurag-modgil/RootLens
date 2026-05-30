import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models import Log, Incident, Cluster
from app.config import settings

# Setup a clean, independent test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_system.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Monkeypatch all imports of SessionLocal to point to TestingSessionLocal
import app.database
import app.agents.sre_agents
import app.main
import app.tasks

app.database.SessionLocal = TestingSessionLocal
app.agents.sre_agents.SessionLocal = TestingSessionLocal
app.main.SessionLocal = TestingSessionLocal
app.tasks.SessionLocal = TestingSessionLocal

# Override get_db in FastAPI
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    # Recreate tables for clean run
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Enable eager configuration for tests to run synchronously
    settings.celery_always_eager = True
    
    yield
    
    Base.metadata.drop_all(bind=engine)

def test_health_and_metrics_endpoints():
    client = TestClient(fastapi_app)
    
    # 1. Test Health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    
    # 2. Test Prometheus Metrics endpoint
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

def test_multi_agent_flow_success():
    client = TestClient(fastapi_app)
    db = TestingSessionLocal()
    
    # Ingest 3 errors for payment-gateway to trigger detection threshold
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    logs_to_send = [
        {"timestamp": now.isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Database connection pool exhausted timeout error"},
        {"timestamp": now.isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Failed to check out: connection pool error"},
        {"timestamp": (now + datetime.timedelta(seconds=1)).isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Database timeout after 30 seconds"}
    ]
    
    # Post first 2 logs (won't trigger spike yet, threshold = 3)
    for log_data in logs_to_send[:2]:
        res = client.post("/api/v1/logs", json=log_data)
        assert res.status_code == 201
        
    # Check no incidents created yet
    incidents = db.query(Incident).all()
    assert len(incidents) == 0

    # Send 3rd log to trigger the spike detection
    res = client.post("/api/v1/logs", json=logs_to_send[2])
    assert res.status_code == 201

    # Check incident was auto-detected and created!
    incidents = db.query(Incident).all()
    assert len(incidents) == 1
    incident = incidents[0]
    
    assert incident.status == "OPEN"
    assert incident.severity == "HIGH"  # payment-gateway is a critical service, ERROR level = HIGH
    assert "payment-gateway" in incident.title
    
    # Check that RCA was run and Remediation was proposed automatically
    assert incident.remediation_status == "PENDING_APPROVAL"
    assert "docker restart" in incident.remediation_action  # From mock RCA database connection rule

    # Approve remediation command execution
    approve_res = client.post(f"/api/v1/dashboard/incidents/{incident.id}/approve")
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "success"

    # Refresh DB and verify results of execution and VerificationAgent scan
    # Since CELERY_ALWAYS_EAGER is True, the event chain executes synchronously!
    # And since we didn't add any new error logs after the remediation timestamp,
    # the VerificationAgent's check (error count == 0) succeeds, resolving the incident.
    db.refresh(incident)
    assert incident.remediation_status == "SUCCESS"
    assert incident.status == "RESOLVED"


def test_multi_agent_flow_failed_verification():
    client = TestClient(fastapi_app)
    db = TestingSessionLocal()
    
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    logs_to_send = [
        {"timestamp": now.isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Database connection pool exhausted timeout error"},
        {"timestamp": now.isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Failed to check out: connection pool error"},
        {"timestamp": (now + datetime.timedelta(seconds=1)).isoformat(), "service_name": "payment-gateway", "log_level": "ERROR", "message": "Database timeout after 30 seconds"}
    ]
    
    # Ingest 3 logs to trigger incident
    for log_data in logs_to_send:
        client.post("/api/v1/logs", json=log_data)
        
    incident = db.query(Incident).first()
    assert incident is not None
    assert incident.remediation_status == "PENDING_APPROVAL"

    # Inject a new error log *simulating* failure after remediation execution time (now)
    # The VerificationAgent scans logs where timestamp >= execution_timestamp.
    # So if we write an error log matching the service, the verification fails.
    err_log = Log(
        timestamp=now + datetime.timedelta(seconds=2),
        service_name="payment-gateway",
        log_level="ERROR",
        message="Post-remediation error persists!"
    )
    db.add(err_log)
    db.commit()

    # Approve and trigger remediation execution
    approve_res = client.post(f"/api/v1/dashboard/incidents/{incident.id}/approve")
    assert approve_res.status_code == 200

    # Refresh and check that verification failed, so remediation_status is FAILED, status is OPEN
    db.refresh(incident)
    assert incident.remediation_status == "FAILED"
    assert incident.status == "OPEN"
