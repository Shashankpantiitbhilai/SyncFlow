"""
Outbound sync worker for sending changes to external systems.
"""
import asyncio
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base_worker import BaseWorker
from ..core import KafkaTopics, AsyncSessionLocal
from ..models import Customer, ExternalMapping, SyncEvent
from ..integrations import StripeIntegration

logger = logging.getLogger(__name__)


class OutboundSyncWorker(BaseWorker):
    """Worker for synchronizing internal changes to external systems."""
    
    def __init__(self):
        # Use a specific consumer group for outbound sync
        super().__init__("outbound-sync", group_id="zenskar-sync-outbound")
        self.stripe_integration = StripeIntegration()
    
    def get_topic(self) -> str:
        """Get the Kafka topic this worker should consume from."""
        return KafkaTopics.SYNC_OUTBOUND
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process customer event message."""
        event_type = message.get("event_type")
        customer_data = message.get("customer_data", {})
        customer_id = customer_data.get("id")
        
        # Skip if this is from a webhook and marked to skip outbound sync
        if message.get("skip_outbound"):
            logger.info(f"Skipping outbound sync for webhook event: {event_type}")
            return
        
        if not customer_id:
            logger.error("No customer ID in message")
            return
        
        async with AsyncSessionLocal() as db:
            try:
                # Create sync event record
                sync_event = SyncEvent(
                    event_type=event_type,
                    entity_type="customer",
                    entity_id=customer_id,
                    external_system="stripe",
                    payload=message,
                    status="pending"
                )
                db.add(sync_event)
                
                # For non-delete operations, get customer data
                if event_type != "customer.deleted":
                    customer = await db.execute(
                        select(Customer).where(Customer.id == customer_id)
                    )
                    customer = customer.scalar_one_or_none()
                    
                    if not customer:
                        logger.error(f"Customer not found: {customer_id}")
                        sync_event.status = "failed"
                        sync_event.error = "Customer not found"
                        await db.commit()
                        return

                # Get existing mapping (will be used for all operations)
                mapping = await db.execute(
                    select(ExternalMapping).where(
                        ExternalMapping.internal_customer_id == customer_id,
                        ExternalMapping.external_system == "stripe"
                    )
                )
                mapping = mapping.scalar_one_or_none()
                
                try:
                    if event_type == "customer.created":
                        if mapping:
                            logger.warning(f"Customer {customer_id} already mapped to Stripe")
                            sync_event.status = "skipped"
                            await db.commit()
                            return
                            
                        # Create in Stripe
                        logger.info(f"Creating customer in Stripe with data: id={customer.id}, name={customer.name}, email={customer.email}")
                        external_id = await self.stripe_integration.create_customer({
                            "id": customer.id,
                            "name": customer.name,
                            "email": customer.email
                        })
                        logger.info(f"Received Stripe customer ID: {external_id}")
                        
                        if not external_id:
                            logger.error("Failed to receive external_id from Stripe")
                            sync_event.status = "failed"
                            sync_event.error = "No external ID received from Stripe"
                            await db.commit()
                            return
                            
                        # Create mapping
                        logger.info(f"Creating external mapping: internal_id={customer.id}, external_id={external_id}")
                        mapping = ExternalMapping(
                            internal_customer_id=customer.id,
                            external_system="stripe",
                            external_id=external_id
                        )
                        db.add(mapping)
                        await db.flush()  # Flush to ensure the mapping is created
                        logger.info(f"External mapping created with ID: {mapping.id}")
                        
                        
                    elif event_type == "customer.updated":
                        if not mapping:
                            logger.error(f"No Stripe mapping for customer {customer_id}")
                            sync_event.status = "failed"
                            sync_event.error = "No Stripe mapping found"
                            await db.commit()
                            return
                            
                        # Update in Stripe
                        await self.stripe_integration.update_customer(
                            mapping.external_id,
                            {
                                "id": customer.id,
                                "name": customer.name,
                                "email": customer.email
                            }
                        )
                        
                    elif event_type == "customer.deleted":
                        # For delete operations, we only need the mapping
                        mapping = await db.execute(
                            select(ExternalMapping).where(
                                ExternalMapping.internal_customer_id == customer_id,
                                ExternalMapping.external_system == "stripe"
                            )
                        )
                        mapping = mapping.scalar_one_or_none()
                        
                        if not mapping:
                            # If no mapping exists, it means either:
                            # 1. Customer was never synced to Stripe
                            # 2. Mapping was already deleted (in case of retries)
                            logger.warning(f"No Stripe mapping for deleted customer {customer_id}")
                            sync_event.status = "skipped"
                            await db.commit()
                            return

                        try:
                            # First try to delete from Stripe
                            await self.stripe_integration.delete_customer(mapping.external_id)
                            logger.info(f"Successfully deleted customer {customer_id} from Stripe")
                            
                            # Only after successful Stripe deletion, remove mapping
                            await db.delete(mapping)
                            logger.info(f"Removed mapping for customer {customer_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to delete customer {customer_id} from Stripe: {e}")
                            sync_event.status = "failed"
                            sync_event.error = str(e)
                            await db.commit()
                            raise
                    
                    from datetime import datetime
                    sync_event.status = "completed"
                    sync_event.processed_at = datetime.utcnow()
                    await db.commit()
                    
                except Exception as e:
                    logger.error(f"Failed to sync customer {customer_id} to Stripe: {e}")
                    sync_event.status = "failed"
                    sync_event.error = str(e)
                    sync_event.retry_count += 1
                    await db.commit()
                    raise
                
            except Exception as e:
                # Update sync event with error
                sync_event.status = "failed"
                sync_event.error_message = str(e)
                sync_event.retry_count += 1
                await db.commit()
                raise
    
    async def _handle_customer_created(
        self, 
        db: AsyncSession, 
        customer_id: int, 
        customer_data: Dict[str, Any],
        sync_event: SyncEvent
    ) -> None:
        """Handle customer creation event."""
        try:
            # Create customer in Stripe
            stripe_customer_id = await self.stripe_integration.create_customer(customer_data)
            
            # Create external mapping
            mapping = ExternalMapping(
                internal_customer_id=customer_id,
                external_system="stripe",
                external_id=stripe_customer_id
            )
            db.add(mapping)
            await db.commit()
            
            logger.info(f"Created customer {customer_id} in Stripe as {stripe_customer_id}")
            
        except Exception as e:
            logger.error(f"Failed to create customer {customer_id} in Stripe: {e}")
            raise
    
    async def _handle_customer_updated(
        self, 
        db: AsyncSession, 
        customer_id: int, 
        customer_data: Dict[str, Any],
        sync_event: SyncEvent
    ) -> None:
        """Handle customer update event."""
        try:
            # Get Stripe customer ID
            result = await db.execute(
                select(ExternalMapping).where(
                    ExternalMapping.internal_customer_id == customer_id,
                    ExternalMapping.external_system == "stripe"
                )
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                logger.warning(f"No Stripe mapping found for customer {customer_id}")
                return
            
            # Update customer in Stripe
            await self.stripe_integration.update_customer(mapping.external_id, customer_data)
            
            logger.info(f"Updated customer {customer_id} in Stripe")
            
        except Exception as e:
            logger.error(f"Failed to update customer {customer_id} in Stripe: {e}")
            raise
    
    async def _handle_customer_deleted(
        self, 
        db: AsyncSession, 
        customer_id: int, 
        customer_data: Dict[str, Any],
        sync_event: SyncEvent
    ) -> None:
        """Handle customer deletion event."""
        try:
            # Get Stripe customer ID
            result = await db.execute(
                select(ExternalMapping).where(
                    ExternalMapping.internal_customer_id == customer_id,
                    ExternalMapping.external_system == "stripe"
                )
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                logger.warning(f"No Stripe mapping found for customer {customer_id}")
                return
            
            # Delete customer in Stripe
            await self.stripe_integration.delete_customer(mapping.external_id)
            
            # Delete the mapping (should already be deleted by cascade)
            await db.delete(mapping)
            await db.commit()
            
            logger.info(f"Deleted customer {customer_id} from Stripe")
            
        except Exception as e:
            logger.error(f"Failed to delete customer {customer_id} from Stripe: {e}")
            raise


async def main():
    """Main function to run the outbound sync worker."""
    worker = OutboundSyncWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
