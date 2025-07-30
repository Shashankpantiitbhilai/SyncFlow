"""
Sync event model for tracking synchronization events.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel
import uuid

from ..core.database import Base


class SyncEvent(Base):
    """Sync event database model."""
    __tablename__ = "sync_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    external_system = Column(String(50))
    status = Column(String(50), default="pending")
    payload = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)


# Pydantic models
class SyncEventBase(BaseModel):
    """Base sync event schema."""
    event_type: str
    entity_type: str
    entity_id: int
    external_system: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class SyncEventCreate(SyncEventBase):
    """Schema for creating a sync event."""
    pass


class SyncEventUpdate(BaseModel):
    """Schema for updating a sync event."""
    status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    processed_at: Optional[datetime] = None


class SyncEventResponse(SyncEventBase):
    """Schema for sync event response."""
    id: int
    event_id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
