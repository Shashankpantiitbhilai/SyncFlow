"""
Customer model definition.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr

from ..core.database import Base
from .external_mapping import ExternalMappingResponse


class Customer(Base):
    """Customer database model."""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    external_mappings = relationship("ExternalMapping", back_populates="customer", cascade="all, delete-orphan")


# Pydantic models for API
class CustomerBase(BaseModel):
    """Base customer schema."""
    name: str
    email: EmailStr


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: int
    created_at: datetime
    updated_at: datetime

class CustomerWithMappings(CustomerResponse):
    """Schema for customer response with external mappings."""
    external_mappings: List[ExternalMappingResponse]
    class Config:
        from_attributes = True


class CustomerWithMappings(CustomerResponse):
    """Customer response with external mappings."""
    external_mappings: List["ExternalMappingResponse"] = []
    
    class Config:
        from_attributes = True


# Import here to avoid circular imports
from .external_mapping import ExternalMappingResponse
