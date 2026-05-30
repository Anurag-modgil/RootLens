from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False, index=True)
    severity = Column(String(50), default="MEDIUM", nullable=False, index=True)
    remediation_status = Column(String(50), nullable=True, index=True)
    remediation_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    clusters = relationship("Cluster", back_populates="incident")

class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="clusters")
    logs = relationship("Log", back_populates="cluster")

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    service_name = Column(String(255), nullable=False, index=True)
    log_level = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    cluster = relationship("Cluster", back_populates="logs")
