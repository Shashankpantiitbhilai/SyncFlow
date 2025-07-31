"""
Inbound sync worker for processing changes from external systems.
"""
import logging
from typing import Dict, Any
from sqlalchemy import select

from .base_worker import BaseWorker
from ..core import KafkaTopics, AsyncSessionLocal
from ..models import Customer, ExternalMapping, SyncEvent
from ..integrations import StripeIntegration

logger = logging.getLogger(__name__)


class InboundSyncWorker(BaseWorker):
    """Worker for processing inbound sync events from external systems."""
    
    def __init__(self):
        # Use a specific consumer group for inbound sync
        super().__init__("inbound-sync", group_id="zenskar-sync-inbound")
        self.stripe_integration = StripeIntegration()
    
    def get_topic(self) -> str:
        """Get the Kafka topic this worker should consume from."""
        return KafkaTopics.SYNC_INBOUND
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process inbound sync event message."""
        source = message.get("source")
        event_type = message.get("event_type")
        customer_data = message.get("data", {})
        external_id = customer_data.get("external_id")
        
        logger.info(f"[INBOUND] Processing message - Type: {event_type}, Source: {source}")
        logger.info(f"[INBOUND] Customer data received: {customer_data}")
        
        if not external_id:
            logger.error("[INBOUND] No external ID in message. Full message: %s", message)
            return
        
        async with AsyncSessionLocal() as db:
            try:
                # Get existing mapping
                logger.info(f"[INBOUND] Checking for existing mapping - External ID: {external_id}, Source: {source}")
                mapping = await db.execute(
                    select(ExternalMapping).where(
                        ExternalMapping.external_id == external_id,
                        ExternalMapping.external_system == source
                    )
                )
                mapping = mapping.scalar_one_or_none()
                
                try:
                    # Initialize sync event as None
                    sync_event = None
                    customer_id = None
                    event_status = "pending"
                    error_message = None

                    if event_type == "customer.created":
                        if mapping:
                            logger.warning(f"[INBOUND] External ID {external_id} already mapped to internal ID {mapping.internal_customer_id}")
                            customer_id = mapping.internal_customer_id
                            event_status = "skipped"
                        else:
                            # Create customer in our system
                            logger.info(f"[INBOUND] Creating new customer - Name: {customer_data.get('name')}, Email: {customer_data.get('email')}")
                            try:
                                customer = Customer(
                                    name=customer_data.get("name", ""),
                                    email=customer_data.get("email", "")
                                )
                                db.add(customer)
                                logger.info("[INBOUND] Added customer to session, flushing to get ID...")
                                await db.flush()  # Get the customer ID
                                logger.info(f"[INBOUND] Customer created successfully with ID: {customer.id}")
                                
                                # Create mapping
                                logger.info(f"[INBOUND] Creating mapping - Internal ID: {customer.id}, External ID: {external_id}")
                                mapping = ExternalMapping(
                                    internal_customer_id=customer.id,
                                    external_system=source,
                                    external_id=external_id
                                )
                                db.add(mapping)
                                logger.info("[INBOUND] Added mapping to session")
                                customer_id = customer.id
                                event_status = "completed"
                            except Exception as e:
                                logger.error(f"[INBOUND] Database error during customer creation: {str(e)}")
                                logger.error(f"[INBOUND] Customer data: {customer_data}")
                                event_status = "failed"
                                error_message = str(e)
                                raise
                        
                    elif event_type == "customer.updated":
                        if not mapping:
                            logger.error(f"No mapping found for {external_id}")
                            event_status = "failed"
                            error_message = "No mapping found"
                        else:
                            # Get customer to update
                            customer = await db.execute(
                                select(Customer).where(
                                    Customer.id == mapping.internal_customer_id
                                )
                            )
                            customer = customer.scalar_one_or_none()
                            
                            if not customer:
                                logger.error(f"Customer not found for mapping {mapping.id}")
                                event_status = "failed"
                                error_message = "Customer not found"
                            else:
                                # Update customer
                                customer.name = customer_data.get("name", customer.name)
                                customer.email = customer_data.get("email", customer.email)
                                customer_id = customer.id
                                event_status = "completed"
                        
                    elif event_type == "customer.deleted":
                        if not mapping:
                            logger.warning(f"No mapping found for deleted customer {external_id}")
                            event_status = "skipped"
                        else:
                            # Get customer to delete
                            customer = await db.execute(
                                select(Customer).where(
                                    Customer.id == mapping.internal_customer_id
                                )
                            )
                            customer = customer.scalar_one_or_none()
                            
                            if customer:
                                customer_id = customer.id
                                await db.delete(customer)
                                event_status = "completed"
                            
                            # Delete mapping
                            await db.delete(mapping)
                    
                    # Now create the sync event with the customer ID
                    sync_event = SyncEvent(
                        event_type=event_type,
                        entity_type="customer",
                        entity_id=customer_id,
                        external_system=source,
                        payload=message,
                        status=event_status,
                        error_message=error_message
                    )
                    db.add(sync_event)
                    
                    logger.info("[INBOUND] Committing transaction...")
                    try:
                        await db.commit()
                        logger.info(f"[INBOUND] Successfully processed {event_type} for {external_id}")
                        logger.info(f"[INBOUND] Final state - Event: {event_status}, Entity ID: {customer_id}")
                    except Exception as commit_error:
                        logger.error(f"[INBOUND] Commit failed: {str(commit_error)}")
                        raise
                    
                except Exception as e:
                    logger.error(f"[INBOUND] Error processing {event_type} for {external_id}")
                    logger.error(f"[INBOUND] Error details: {str(e)}")
                    logger.error(f"[INBOUND] Customer data: {customer_data}")
                    try:
                        if not sync_event:
                            # Create a failed sync event if we haven't created one yet
                            sync_event = SyncEvent(
                                event_type=event_type,
                                entity_type="customer",
                                entity_id=customer_id if customer_id else None,
                                external_system=source,
                                payload=message,
                                status="failed",
                                error_message=str(e)
                            )
                            db.add(sync_event)
                        await db.commit()
                    except Exception as commit_error:
                        logger.error(f"[INBOUND] Failed to commit error status: {str(commit_error)}")
                    raise
                    
            except Exception as e:
                logger.error(f"Database error processing {event_type}: {e}")
                raise
