import logging
import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Log, Incident, Cluster

logger = logging.getLogger("rootlens.detection")

class IncidentDetectionEngine:
    def __init__(self):
        pass

    def run_detection(self, db: Session) -> List[Incident]:
        """
        Main runner for incident detection. Scan for spikes and unassigned error clusters,
        generate SQL Incident entries, and return them.
        """
        logger.info("Running incident detection scan...")
        detected_incidents = []

        # 1. Scan for recent error/critical log spikes
        spikes = self._detect_log_spikes(db)
        for spike in spikes:
            incident = self._create_incident_for_spike(db, spike)
            if incident:
                detected_incidents.append(incident)

        # 2. Scan for unassigned clusters containing errors
        unassigned_clusters = db.query(Cluster).filter(Cluster.incident_id == None).all()
        for cluster in unassigned_clusters:
            # Check if this cluster contains errors
            error_logs = db.query(Log).filter(
                Log.cluster_id == cluster.id,
                Log.log_level.in_(["ERROR", "CRITICAL", "FATAL"])
            ).all()

            if error_logs:
                incident = self._create_incident_for_cluster(db, cluster, error_logs)
                if incident:
                    detected_incidents.append(incident)

        return detected_incidents

    def _detect_log_spikes(self, db: Session, window_mins: int = 5, threshold_count: int = 3) -> List[dict]:
        """
        Detect spikes in logs (log level >= ERROR) in the last window_mins.
        If the count of error logs for a service in the window is >= threshold_count, trigger a spike.
        """
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        cutoff = now - datetime.timedelta(minutes=window_mins)

        # Query counts grouped by service and level
        results = db.query(
            Log.service_name,
            Log.log_level,
            func.count(Log.id).label("log_count")
        ).filter(
            Log.timestamp >= cutoff,
            Log.log_level.in_(["ERROR", "CRITICAL", "FATAL"])
        ).group_by(
            Log.service_name,
            Log.log_level
        ).all()

        spikes = []
        for service, level, count in results:
            if count >= threshold_count:
                logger.warning(f"Detected log spike for service '{service}' (level: {level}, count: {count})")
                spikes.append({
                    "service_name": service,
                    "log_level": level,
                    "count": count
                })
        return spikes

    def _create_incident_for_spike(self, db: Session, spike: dict) -> Optional[Incident]:
        """
        Create a database Incident record for a detected log volume spike.
        """
        service = spike["service_name"]
        level = spike["log_level"]
        count = spike["count"]

        title = f"Alert: High Error Volume on {service}"
        
        # Check if an open incident already exists for this service with a similar title
        existing = db.query(Incident).filter(
            Incident.title == title,
            Incident.status == "OPEN"
        ).first()
        if existing:
            return None

        # Resolve severity mapping
        severity = self._map_severity(service, level)

        incident = Incident(
            title=title,
            description=f"Log spike detected on service '{service}'. Found {count} logs of level '{level}' in the last {5} minutes.",
            status="OPEN",
            severity=severity
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        logger.info(f"Created Incident ID {incident.id} (Severity: {severity}) for log spike on '{service}'.")
        return incident

    def _create_incident_for_cluster(self, db: Session, cluster: Cluster, error_logs: List[Log]) -> Optional[Incident]:
        """
        Create an Incident for a cluster that contains error logs but doesn't have an incident.
        """
        title = f"Incident for Cluster: {cluster.name}"
        
        # Check if open incident exists
        existing = db.query(Incident).filter(
            Incident.title == title,
            Incident.status == "OPEN"
        ).first()
        if existing:
            cluster.incident_id = existing.id
            db.commit()
            return None

        # Map severity based on logs
        levels = [l.log_level for l in error_logs]
        services = [l.service_name for l in error_logs]
        
        highest_level = "ERROR"
        if "CRITICAL" in levels or "FATAL" in levels:
            highest_level = "CRITICAL"
            
        most_common_svc = max(set(services), key=services.count) if services else "unknown"
        severity = self._map_severity(most_common_svc, highest_level)

        incident = Incident(
            title=title,
            description=f"Auto-generated incident for cluster ID {cluster.id} containing {len(error_logs)} error logs.",
            status="OPEN",
            severity=severity
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        # Link cluster to incident
        cluster.incident_id = incident.id
        db.commit()
        
        logger.info(f"Created Incident ID {incident.id} for Cluster '{cluster.name}'.")
        return incident

    def _map_severity(self, service: str, level: str) -> str:
        """
        Severity assignment rules: Low, Medium, High, Critical
        """
        level_upper = level.upper()
        service_lower = service.lower()

        # Core critical services list
        critical_services = ["payment", "auth", "billing", "database", "gateway", "redis"]

        if level_upper in ["CRITICAL", "FATAL"]:
            return "CRITICAL"
            
        if level_upper == "ERROR":
            if any(cs in service_lower for cs in critical_services):
                return "HIGH"
            return "MEDIUM"
            
        if level_upper == "WARNING":
            if any(cs in service_lower for cs in critical_services):
                return "MEDIUM"
            return "LOW"

        return "LOW"
