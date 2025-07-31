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
        
        # Verify webhook signature
        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
            
        # Parse and verify the webhook
        try:
            from ...integrations.stripe.client import StripeIntegration
            stripe_client = StripeIntegration()
            
            # Verify the signature using Stripe's library
            import stripe
            event = stripe.Webhook.construct_event(
                payload=body,
                sig_header=stripe_signature,
                secret=stripe_client.webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error verifying webhook signature"
            )

        logger.info(f"Received Stripe webhook: {event.get('type', 'unknown')}")
        logger.info(f"Event data: {event.get('data', {})}")
        
        # Filter for customer events
        if event.get("type", "").startswith("customer."):
            # Transform customer data for our system
            customer_data = stripe_client.transform_external_to_internal(event['data']['object'])
            
            # Create sync event message
            message = {
                "source": "stripe",
                "event_type": event.get("type"),
                "data": customer_data,
                "skip_outbound": True,  # Flag to prevent loops
                "metadata": {
                    "stripe_event_id": event.get("id"),
                    "stripe_event_type": event.get("type"),
                    "stripe_created": event.get("created"),
                }
            }
            
            # Publish to Kafka for processing
            await kafka_client.produce_message(
                KafkaTopics.SYNC_INBOUND,
                message
            )
            
            logger.info(f"Published Stripe event to sync queue: {event.get('id')}")
        
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
