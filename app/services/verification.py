import logging
import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Log, Incident

logger = logging.getLogger("rootlens.verification")

class VerificationAgent:
    def __init__(self):
        pass

    def verify_remediation(
        self,
        db: Session,
        incident_id: int,
        remediation_timestamp: datetime.datetime,
        observation_window_seconds: int = 30
    ) -> bool:
        """
        Scans logs generated AFTER the remediation action was executed.
        Returns True if the error rate dropped (resolved), False otherwise.
        """
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            logger.error(f"Incident ID {incident_id} not found.")
            return False

        service_name = self._extract_service_from_incident(incident)
        logger.info(f"Running SRE Verification for service '{service_name}' post-remediation timestamp: {remediation_timestamp}")

        # Scan for logs generated after remediation_timestamp
        cutoff_time = remediation_timestamp + datetime.timedelta(seconds=observation_window_seconds)
        
        # Check error counts in the window
        error_count = db.query(func.count(Log.id)).filter(
            Log.service_name == service_name,
            Log.log_level.in_(["ERROR", "CRITICAL", "FATAL"]),
            Log.timestamp >= remediation_timestamp,
            Log.timestamp <= cutoff_time
        ).scalar()

        logger.info(f"Verification scan results: found {error_count} new errors in observation window for service '{service_name}'.")

        # Threshold check: if error count is 0, we consider it successfully resolved!
        if error_count == 0:
            logger.info(f"Verification SUCCESS: No new errors detected. Incident ID {incident_id} marked as RESOLVED.")
            incident.status = "RESOLVED"
            incident.remediation_status = "SUCCESS"
            db.commit()
            return True
        else:
            logger.warning(f"Verification FAILED: {error_count} errors persist post-remediation. Incident ID {incident_id} remains UNRESOLVED.")
            incident.remediation_status = "FAILED"
            incident.status = "OPEN"
            db.commit()
            return False

    def _extract_service_from_incident(self, incident: Incident) -> str:
        """
        Parse service name from incident title (e.g. 'Alert: High Error Volume on payment-gateway')
        """
        title = incident.title
        if "on " in title:
            return title.split("on ")[-1].strip()
        if "Cluster: " in title:
            parts = title.split("Cluster: ")
            if len(parts) > 2:
                return parts[2].split(" - ")[0].strip()
            return parts[-1].split(" - ")[0].strip()
        
        return "unknown"
