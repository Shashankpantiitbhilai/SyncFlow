"""
Webhook API routes for external system integrations.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional

from ...core import kafka_client, KafkaTopics, settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """Handle Stripe webhook events."""
    try:
        # Get the raw body
        body = await request.body()
        
        # Verify webhook signature (will implement in stripe integration)
        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Parse webhook event
        try:
            import json
            event = json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Log the event
        logger.info(f"Received Stripe webhook: {event.get('type', 'unknown')}")
        
        # Filter for customer events
        if event.get("type", "").startswith("customer."):
            # Publish to inbound sync queue
            await kafka_client.produce_message(
                KafkaTopics.SYNC_INBOUND,
                {
                    "source": "stripe",
                    "event_type": event.get("type"),
                    "stripe_event": event
                }
            )
            logger.info(f"Published Stripe event to inbound sync: {event.get('id')}")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process Stripe webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.post("/salesforce")
async def salesforce_webhook(request: Request):
    """Handle Salesforce webhook events (placeholder for future implementation)."""
    try:
        body = await request.body()
        
        # Parse webhook event
        try:
            import json
            event = json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        logger.info("Received Salesforce webhook")
        
        # Publish to inbound sync queue
        await kafka_client.produce_message(
            KafkaTopics.SYNC_INBOUND,
            {
                "source": "salesforce",
                "salesforce_event": event
            }
        )
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process Salesforce webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.get("/health")
async def webhook_health():
    """Webhook health check endpoint."""
    return {
        "status": "healthy",
        "webhooks": {
            "stripe": "enabled",
            "salesforce": "enabled"
        }
    }
