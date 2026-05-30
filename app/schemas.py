from pydantic import BaseModel, Field
from datetime import datetime

class LogCreate(BaseModel):
    timestamp: datetime = Field(description="The timestamp when the log event occurred (UTC)")
    service_name: str = Field(..., min_length=1, max_length=255, description="Name of the service generating the log")
    log_level: str = Field(..., min_length=1, max_length=50, description="Log level: INFO, WARNING, ERROR, etc.")
    message: str = Field(..., min_length=1, description="The detailed log message")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-05-30T11:53:51Z",
                "service_name": "auth-service",
                "log_level": "ERROR",
                "message": "Failed to connect to database: connection timeout"
            }
        }

class LogResponse(BaseModel):
    id: int
    timestamp: datetime
    service_name: str
    log_level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

class IngestSuccessResponse(BaseModel):
    status: str = "success"
    message: str = "Log ingested successfully"
    log: LogResponse
