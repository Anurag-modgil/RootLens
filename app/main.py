from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
from app.config import settings
from app.database import engine, SessionLocal
from app.api.logs import router as logs_router
from app.api.dashboard import router as dashboard_router
from app.services.websocket import manager as ws_manager
from app.agents.orchestrator import orchestrator
from app.agents.sre_agents import LogAnalysisAgent, ClusteringAgent, RCAAgent, RemediationAgent, VerificationAgent

# Initialize SRE Agents and register them with the orchestrator
analysis_agent = LogAnalysisAgent()
clustering_agent = ClusteringAgent()
rca_agent = RCAAgent()
remediation_agent = RemediationAgent()
verification_agent = VerificationAgent()

orchestrator.register_agent(analysis_agent)
orchestrator.register_agent(clustering_agent)
orchestrator.register_agent(rca_agent)
orchestrator.register_agent(remediation_agent)
orchestrator.register_agent(verification_agent)

# Store remediation_agent on orchestrator class for manual approval triggering
orchestrator.remediation_agent = remediation_agent

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# Prometheus Metrics definitions
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"])
INGESTED_LOGS = Counter("rootlens_ingested_logs_total", "Total Ingested Logs")
ACTIVE_INCIDENTS = Gauge("rootlens_active_incidents", "Active Open Incidents Count")

@app.middleware("http")
async def monitor_requests(request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=response.status_code
    ).inc()
    return response

# Root endpoint
@app.get("/")
def read_root():
    return {
        "app": settings.app_name,
        "status": "healthy",
        "documentation": "/docs"
    }

# Prometheus Metrics Endpoint
@app.get("/metrics")
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Health Check Endpoint
@app.get("/health")
def health_check():
    health = {"status": "healthy", "components": {}}
    
    # 1. Test database connection
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        health["components"]["database"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["components"]["database"] = f"failed: {str(e)}"
    finally:
        db.close()

    # 2. Test Qdrant connectivity
    try:
        from app.services.vector_store import VectorStoreService
        vs = VectorStoreService()
        vs._client.get_collections()
        health["components"]["qdrant"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["components"]["qdrant"] = f"failed: {str(e)}"

    return health

# WebSockets update stream endpoint
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)

# Include API routes
app.include_router(logs_router)
app.include_router(dashboard_router)
