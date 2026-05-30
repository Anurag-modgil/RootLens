import logging
from sqlalchemy.orm import Session
from app.models import Incident
from app.services.executor import SafeCommandExecutor

logger = logging.getLogger("rootlens.remediation")

class RemediationAgent:
    def __init__(self):
        self.executor = SafeCommandExecutor()

    def propose_remediation(self, db: Session, incident: Incident, rca_output: dict) -> Incident:
        """
        Receives RCA diagnostic results, suggests fixes, drafts recovery commands,
        sets execution state to PENDING_APPROVAL, and logs details.
        """
        fix = rca_output.get("recommended_fix", "echo 'No action proposed.'")

        logger.info(f"Proposing remediation for Incident ID {incident.id}: '{fix}'")

        incident.remediation_status = "PENDING_APPROVAL"
        incident.remediation_action = fix
        db.commit()
        db.refresh(incident)

        logger.info(f"Incident ID {incident.id} status updated to PENDING_APPROVAL.")
        return incident

    def execute_approved_remediation(self, db: Session, incident_id: int) -> bool:
        """
        Runs the proposed command if approval state is met. Logs execution metrics and results.
        """
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            logger.error(f"Incident ID {incident_id} not found.")
            return False

        if incident.remediation_status != "PENDING_APPROVAL":
            logger.warning(f"Remediation execution aborted: Incident ID {incident_id} state is '{incident.remediation_status}', expected 'PENDING_APPROVAL'.")
            return False

        command = incident.remediation_action
        logger.info(f"Remediation execution APPROVED for Incident ID {incident_id}. Command: '{command}'")
        
        # 1. Update status to EXECUTING
        incident.remediation_status = "EXECUTING"
        db.commit()

        # 2. Spawn Safe Executor
        result = self.executor.execute_command(command)
        
        # 3. Log results and update incident outcome
        if result["status"] == "success":
            logger.info(f"Remediation command succeeded for Incident ID {incident_id}: {result['output']}")
            incident.remediation_status = "SUCCESS"
            incident.status = "RESOLVED"
            db.commit()
            return True
        else:
            logger.error(f"Remediation command failed for Incident ID {incident_id}: {result['error']}")
            incident.remediation_status = "FAILED"
            db.commit()
            return False
