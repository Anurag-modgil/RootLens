import logging
import datetime
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.database import SessionLocal
from app.models import Log, Incident, Cluster
from app.services.embeddings import LogEmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.clustering import ClusteringService
from app.services.detection import IncidentDetectionEngine
from app.services.rag import RAGService
from app.services.rca import RootCauseAnalysisEngine
from app.services.remediation import RemediationAgent as RemediationService
from app.services.verification import VerificationAgent as VerificationService

logger = logging.getLogger("rootlens.agents")

class LogAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__("LogAnalysisAgent")
        self.embedding_service = LogEmbeddingService()
        self.vector_store = VectorStoreService()

    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        if event_type == "raw_log_ingested":
            log_id = data["log_id"]
            logger.info(f"[{self.name}] Analyzing Log ID: {log_id}")
            
            db = SessionLocal()
            try:
                log_entry = db.query(Log).filter(Log.id == log_id).first()
                if log_entry:
                    vec = self.embedding_service.get_embedding(log_entry.message)
                    payload = {
                        "log_id": log_entry.id,
                        "service_name": log_entry.service_name,
                        "log_level": log_entry.log_level,
                        "timestamp": log_entry.timestamp.isoformat(),
                        "message": log_entry.message,
                        "cluster_id": log_entry.cluster_id,
                        "incident_id": None
                    }
                    self.vector_store.upsert_log(log_id, vec, payload)
                    logger.info(f"[{self.name}] Successfully indexed Log ID {log_id} in Qdrant.")
                    
                    # Fire next event
                    orchestrator.dispatch_event("log_ingested", payload)
            finally:
                db.close()

class ClusteringAgent(BaseAgent):
    def __init__(self):
        super().__init__("ClusteringAgent")
        self.clustering_service = ClusteringService()
        self.detection_engine = IncidentDetectionEngine()

    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        if event_type == "log_ingested":
            logger.info(f"[{self.name}] New log ingested. Running clustering and incident detection check...")
            db = SessionLocal()
            try:
                # 1. Run HDBSCAN
                self.clustering_service.run_clustering(db)
                
                # 2. Run Incident Detection to find spikes
                detected_incidents = self.detection_engine.run_detection(db)
                for incident in detected_incidents:
                    orchestrator.dispatch_event("incident_detected", {
                        "incident_id": incident.id,
                        "title": incident.title,
                        "severity": incident.severity
                    })
            finally:
                db.close()

class RCAAgent(BaseAgent):
    def __init__(self):
        super().__init__("RCAAgent")
        self.rag_service = RAGService()
        self.rca_engine = RootCauseAnalysisEngine()

    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        if event_type == "incident_detected":
            incident_id = data["incident_id"]
            logger.info(f"[{self.name}] Conducting RCA for Incident ID: {incident_id}")
            db = SessionLocal()
            try:
                incident = db.query(Incident).filter(Incident.id == incident_id).first()
                if incident:
                    # Retrieve matching logs
                    service_name = "unknown"
                    if "on " in incident.title:
                        service_name = incident.title.split("on ")[-1].strip()
                    
                    logs = db.query(Log).filter(Log.service_name == service_name).all()
                    
                    # 1. Query RAG solutions
                    query_text = f"Title: {incident.title}\nDescription: {incident.description}"
                    solutions = self.rag_service.search_solutions(query_text, limit=2)
                    
                    # 2. Call OpenAI
                    service_metadata = {"service": service_name, "env": "prod"}
                    rca_output = self.rca_engine.analyze_incident(
                        incident=incident,
                        logs=logs,
                        service_metadata=service_metadata,
                        historical_resolutions=solutions
                    )
                    
                    # Force default solution from RAG if using mock OpenAI model
                    if self.rca_engine.client is None and solutions:
                        rca_output["recommended_fix"] = solutions[0]["solution"]

                    logger.info(f"[{self.name}] RCA completed. Proposing fix: '{rca_output['recommended_fix']}'")
                    orchestrator.dispatch_event("rca_completed", {
                        "incident_id": incident_id,
                        "rca_output": rca_output
                    })
            finally:
                db.close()

class RemediationAgent(BaseAgent):
    def __init__(self):
        super().__init__("RemediationAgent")
        self.remediation_service = RemediationService()

    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        if event_type == "rca_completed":
            incident_id = data["incident_id"]
            rca_output = data["rca_output"]
            logger.info(f"[{self.name}] Formulating remediation for Incident ID: {incident_id}")
            db = SessionLocal()
            try:
                incident = db.query(Incident).filter(Incident.id == incident_id).first()
                if incident:
                    self.remediation_service.propose_remediation(db, incident, rca_output)
                    orchestrator.dispatch_event("remediation_proposed", {
                        "incident_id": incident_id,
                        "proposed_action": incident.remediation_action
                    })
            finally:
                db.close()

    def approve_and_execute(self, incident_id: int, orchestrator: Any):
        """
        Manually trigger the execution of proposed actions.
        """
        logger.info(f"[{self.name}] Action execution approved for Incident ID: {incident_id}")
        db = SessionLocal()
        try:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident:
                exec_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                success = self.remediation_service.execute_approved_remediation(db, incident_id)
                
                orchestrator.dispatch_event("remediation_executed", {
                    "incident_id": incident_id,
                    "success": success,
                    "exec_time": exec_time
                })
        finally:
            db.close()

class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("VerificationAgent")
        self.verification_service = VerificationService()

    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        if event_type == "remediation_executed":
            incident_id = data["incident_id"]
            exec_time = data["exec_time"]
            logger.info(f"[{self.name}] Verifying resolution for Incident ID: {incident_id}")
            db = SessionLocal()
            try:
                resolved = self.verification_service.verify_remediation(
                    db=db,
                    incident_id=incident_id,
                    remediation_timestamp=exec_time,
                    observation_window_seconds=5
                )
                if resolved:
                    orchestrator.dispatch_event("incident_resolved", {"incident_id": incident_id})
                else:
                    orchestrator.dispatch_event("incident_failed", {"incident_id": incident_id})
            finally:
                db.close()
