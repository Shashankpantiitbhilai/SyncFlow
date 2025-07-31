"""
Customer API routes.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...core import get_db, kafka_client, KafkaTopics
from ...models import (
    Customer, 
    CustomerCreate, 
    CustomerUpdate, 
    CustomerResponse, 
    CustomerWithMappings
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all customers with pagination."""
    try:
        result = await db.execute(
            select(Customer)
            .offset(skip)
            .limit(limit)
            .order_by(Customer.created_at.desc())
        )
        customers = result.scalars().all()
        return customers
    except Exception as e:
        logger.error(f"Failed to fetch customers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch customers"
        )


@router.get("/{customer_id}", response_model=CustomerWithMappings)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific customer by ID."""
    try:
        result = await db.execute(
            select(Customer)
            .options(selectinload(Customer.external_mappings))
            .where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        return customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch customer"
        )


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new customer."""
    try:
        # Check if customer with email already exists
        result = await db.execute(
            select(Customer).where(Customer.email == customer_data.email)
        )
        existing_customer = result.scalar_one_or_none()
        
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists"
            )
        
        # Create new customer
        customer = Customer(**customer_data.model_dump())
        db.add(customer)
        await db.flush()  # Flush to get the customer ID
        
        await db.commit()
        await db.refresh(customer)
        
        # Publish event to Kafka - this will handle outbound sync as well
        await _publish_customer_event("customer.created", customer)
        
        logger.info(f"Created customer: {customer.id}")
        return customer
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer"
        )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing customer."""
    try:
        # Get existing customer
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Check email uniqueness if email is being updated
        if customer_data.email and customer_data.email != customer.email:
            result = await db.execute(
                select(Customer).where(Customer.email == customer_data.email)
            )
            existing_customer = result.scalar_one_or_none()
            
            if existing_customer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer with this email already exists"
                )
        
        # Update customer fields
        update_data = customer_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        
        await db.commit()
        await db.refresh(customer)
        
        # Publish event to Kafka
        await _publish_customer_event("customer.updated", customer)
        
        logger.info(f"Updated customer: {customer.id}")
        return customer
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer"
        )


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a customer."""
    try:
        # Get existing customer
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Store customer data for event before deletion
        customer_data = {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email
        }
        
        # First publish the event to Kafka so worker can process before the mapping is deleted
        await _publish_customer_event("customer.deleted", customer_data)
        
        # Then delete customer (cascades to external_mappings)
        await db.delete(customer)
        await db.commit()
        
        logger.info(f"Deleted customer: {customer_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete customer"
        )


async def _publish_customer_event(event_type: str, customer_data):
    """Publish customer event to Kafka."""
    try:
        # Convert customer object to dict if needed
        if hasattr(customer_data, 'id'):
            data = {
                "id": customer_data.id,
                "name": customer_data.name,
                "email": customer_data.email
            }
        else:
            data = customer_data
        
        event = {
            "event_type": event_type,
            "entity_type": "customer",
            "entity_id": data["id"],
            "source": "internal",
            "customer_data": data
        }
        
        await kafka_client.produce_message(
            KafkaTopics.SYNC_OUTBOUND,
            event,
            key=str(data["id"])
        )
        
    except Exception as e:
        logger.error(f"Failed to publish customer event: {e}")
        # Don't fail the API request if event publishing fails
