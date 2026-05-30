from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
from typing import List, Optional
from app.database import get_db
from app.models import Log, Incident, Cluster
from app.agents.orchestrator import orchestrator

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    try:
        # Total counts
        total_logs = db.query(func.count(Log.id)).scalar() or 0
        total_incidents = db.query(func.count(Incident.id)).scalar() or 0
        active_incidents = db.query(func.count(Incident.id)).filter(Incident.status != "RESOLVED").scalar() or 0
        total_clusters = db.query(func.count(Cluster.id)).scalar() or 0

        # Severity counts
        sevs = db.query(Incident.severity, func.count(Incident.id)).group_by(Incident.severity).all()
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for sev, count in sevs:
            if sev in severity_counts:
                severity_counts[sev] = count

        # Service error distribution
        services = db.query(Log.service_name, func.count(Log.id)).group_by(Log.service_name).all()
        service_stats = []
        for svc_name, count in services:
            err_count = db.query(func.count(Log.id)).filter(
                Log.service_name == svc_name,
                Log.log_level.in_(["ERROR", "CRITICAL", "FATAL"])
            ).scalar() or 0
            
            # Simple heuristic status
            health_status = "healthy"
            if err_count > 10:
                health_status = "critical"
            elif err_count > 0:
                health_status = "warning"
                
            service_stats.append({
                "name": svc_name,
                "total_logs": count,
                "error_logs": err_count,
                "status": health_status
            })

        # Ingestion trend over last 7 hours (hourly bins)
        trend = []
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        for i in range(6, -1, -1):
            h_start = now - datetime.timedelta(hours=i+1)
            h_end = now - datetime.timedelta(hours=i)
            
            log_count = db.query(func.count(Log.id)).filter(
                Log.timestamp >= h_start,
                Log.timestamp < h_end
            ).scalar() or 0
            
            err_count = db.query(func.count(Log.id)).filter(
                Log.timestamp >= h_start,
                Log.timestamp < h_end,
                Log.log_level.in_(["ERROR", "CRITICAL", "FATAL"])
            ).scalar() or 0
            
            trend.append({
                "time": h_end.strftime("%H:%M"),
                "logs": log_count,
                "errors": err_count
            })

        return {
            "total_logs": total_logs,
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "total_clusters": total_clusters,
            "severity_counts": severity_counts,
            "service_stats": service_stats,
            "ingestion_trend": trend
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/incidents")
def get_incidents(severity: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(Incident)
        if severity:
            query = query.filter(Incident.severity == severity.upper())
        if status:
            query = query.filter(Incident.status == status.upper())
        
        incidents = query.order_by(Incident.created_at.desc()).all()
        
        result = []
        for inc in incidents:
            # Get clusters associated
            clusters = db.query(Cluster).filter(Cluster.incident_id == inc.id).all()
            cluster_details = []
            for c in clusters:
                log_count = db.query(func.count(Log.id)).filter(Log.cluster_id == c.id).scalar() or 0
                cluster_details.append({
                    "id": c.id,
                    "name": c.name,
                    "summary": c.summary,
                    "log_count": log_count
                })
            
            result.append({
                "id": inc.id,
                "title": inc.title,
                "description": inc.description,
                "status": inc.status,
                "severity": inc.severity,
                "remediation_status": inc.remediation_status,
                "remediation_action": inc.remediation_action,
                "created_at": inc.created_at.isoformat(),
                "updated_at": inc.updated_at.isoformat(),
                "clusters": cluster_details
            })
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/incidents/{incident_id}")
def get_incident_details(incident_id: int, db: Session = Depends(get_db)):
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            raise HTTPException(status_code=404, detail="Incident not found")
            
        # Get clusters associated
        clusters = db.query(Cluster).filter(Cluster.incident_id == inc.id).all()
        cluster_details = []
        related_logs = []
        
        for c in clusters:
            logs = db.query(Log).filter(Log.cluster_id == c.id).order_by(Log.timestamp.desc()).limit(50).all()
            log_list = [{
                "id": l.id,
                "timestamp": l.timestamp.isoformat(),
                "service_name": l.service_name,
                "log_level": l.log_level,
                "message": l.message
            } for l in logs]
            
            cluster_details.append({
                "id": c.id,
                "name": c.name,
                "summary": c.summary,
                "log_count": len(logs)
            })
            related_logs.extend(log_list)
            
        # Sort related logs by timestamp descending
        related_logs.sort(key=lambda x: x["timestamp"], reverse=True)
            
        return {
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "status": inc.status,
            "severity": inc.severity,
            "remediation_status": inc.remediation_status,
            "remediation_action": inc.remediation_action,
            "created_at": inc.created_at.isoformat(),
            "updated_at": inc.updated_at.isoformat(),
            "clusters": cluster_details,
            "logs": related_logs[:100]  # Limit to top 100 logs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/incidents/{incident_id}/approve")
def approve_remediation(incident_id: int, db: Session = Depends(get_db)):
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
            
        if incident.remediation_status != "PENDING_APPROVAL":
            raise HTTPException(
                status_code=400,
                detail=f"Remediation for incident {incident_id} is in status '{incident.remediation_status}', expected 'PENDING_APPROVAL'."
            )
            
        # Trigger approval & async/sync execution via Orchestrator's remediation agent
        # Run it in background or inline. Since this is an SRE command execution, we execute and broadcast events.
        # The orchestrator's remediation_agent handles database updates and fires events.
        remediation_agent = getattr(orchestrator, "remediation_agent", None)
        if not remediation_agent:
            raise HTTPException(status_code=500, detail="Orchestrator SRE Remediation Agent not initialized.")
            
        # Trigger approve_and_execute
        remediation_agent.approve_and_execute(incident_id, orchestrator)
        
        # Reload incident status
        db.refresh(incident)
        return {
            "status": "success",
            "message": "Remediation command execution triggered",
            "remediation_status": incident.remediation_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters")
def get_clusters(db: Session = Depends(get_db)):
    try:
        clusters = db.query(Cluster).all()
        result = []
        for c in clusters:
            log_count = db.query(func.count(Log.id)).filter(Log.cluster_id == c.id).scalar() or 0
            
            # Fetch sample logs
            sample_logs = db.query(Log).filter(Log.cluster_id == c.id).limit(5).all()
            samples = [{
                "id": l.id,
                "timestamp": l.timestamp.isoformat(),
                "service_name": l.service_name,
                "log_level": l.log_level,
                "message": l.message
            } for l in sample_logs]
            
            result.append({
                "id": c.id,
                "name": c.name,
                "summary": c.summary,
                "log_count": log_count,
                "created_at": c.created_at.isoformat(),
                "samples": samples
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/remediations")
def get_remediations(db: Session = Depends(get_db)):
    try:
        incidents = db.query(Incident).filter(
            Incident.remediation_action.isnot(None)
        ).order_by(Incident.updated_at.desc()).all()
        
        result = []
        for inc in incidents:
            result.append({
                "incident_id": inc.id,
                "incident_title": inc.title,
                "action": inc.remediation_action,
                "status": inc.remediation_status,
                "updated_at": inc.updated_at.isoformat()
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
