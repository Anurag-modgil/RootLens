from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Log
from app.schemas import LogCreate, IngestSuccessResponse

router = APIRouter(prefix="/api/v1", tags=["Logs"])

@router.post("/logs", response_model=IngestSuccessResponse, status_code=status.HTTP_201_CREATED)
def ingest_log(log_in: LogCreate, db: Session = Depends(get_db)):
    try:
        db_log = Log(
            timestamp=log_in.timestamp.replace(tzinfo=None),
            service_name=log_in.service_name,
            log_level=log_in.log_level.upper(),
            message=log_in.message
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return IngestSuccessResponse(
            status="success",
            message="Log ingested successfully",
            log=db_log
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save log to database: {str(e)}"
        )
