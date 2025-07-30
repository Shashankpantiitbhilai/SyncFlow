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
        super().__init__("outbound-sync")
        self.stripe_integration = StripeIntegration()
    
    def get_topic(self) -> str:
        """Get the Kafka topic this worker should consume from."""
        return KafkaTopics.CUSTOMER_EVENTS
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process customer event message."""
        event_type = message.get("event_type")
        customer_data = message.get("customer_data", {})
        customer_id = customer_data.get("id")
        
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
                    payload=message
                )
                db.add(sync_event)
                await db.commit()
                await db.refresh(sync_event)
                
                # Process the event
                if event_type == "customer.created":
                    await self._handle_customer_created(db, customer_id, customer_data, sync_event)
                elif event_type == "customer.updated":
                    await self._handle_customer_updated(db, customer_id, customer_data, sync_event)
                elif event_type == "customer.deleted":
                    await self._handle_customer_deleted(db, customer_id, customer_data, sync_event)
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    return
                
                # Update sync event as processed
                sync_event.status = "completed"
                sync_event.processed_at = asyncio.get_event_loop().time()
                await db.commit()
                
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
