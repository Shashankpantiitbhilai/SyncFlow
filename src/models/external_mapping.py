"""
External mapping model for tracking external system IDs.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from pydantic import BaseModel

from ..core.database import Base


class ExternalMapping(Base):
    """External mapping database model."""
    __tablename__ = "external_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    external_system = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="external_mappings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('external_system', 'external_id'),
        UniqueConstraint('internal_customer_id', 'external_system'),
    )


# Pydantic models
class ExternalMappingBase(BaseModel):
    """Base external mapping schema."""
    external_system: str
    external_id: str


class ExternalMappingCreate(ExternalMappingBase):
    """Schema for creating an external mapping."""
    internal_customer_id: int


class ExternalMappingResponse(ExternalMappingBase):
    """Schema for external mapping response."""
    id: int
    internal_customer_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
