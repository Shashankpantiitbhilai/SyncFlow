"""
Stripe API client for customer management.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
import stripe

from ..base import (
    BaseIntegration,
    IntegrationError,
    CustomerNotFoundError,
    CustomerAlreadyExistsError,
    RateLimitError,
    AuthenticationError
)
from ...core import settings

logger = logging.getLogger(__name__)


class StripeIntegration(BaseIntegration):
    """Stripe integration for customer synchronization."""

    def __init__(self):
        super().__init__("stripe")
        if not settings.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is not set")
        if not settings.stripe_webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET environment variable is not set")

        stripe.api_key = settings.stripe_secret_key
        stripe.api_version = settings.stripe_api_version
        self.webhook_secret = settings.stripe_webhook_secret

    def transform_internal_to_external(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform internal customer data to Stripe format."""
        stripe_data = {}
        if "name" in customer_data:
            stripe_data["name"] = customer_data["name"]
        if "email" in customer_data:
            stripe_data["email"] = customer_data["email"]
        stripe_data["metadata"] = {"internal_id": str(customer_data.get("id", ""))}
        return stripe_data

    def transform_external_to_internal(self, stripe_customer) -> Dict[str, Any]:
        """Transform Stripe customer data to internal format."""
        return {
            "external_id": stripe_customer.id,
            "name": stripe_customer.name or "",
            "email": stripe_customer.email or "",
            "external_created_at": stripe_customer.created,
            "external_data": {
                "stripe_id": stripe_customer.id,
                "description": stripe_customer.description,
                "metadata": stripe_customer.metadata,
            },
        }

    async def _run_stripe_operation(self, operation):
        """Run a Stripe operation with error handling."""
        try:
            return await asyncio.to_thread(operation)
        except stripe.error.InvalidRequestError as e:
            if "already exists" in str(e).lower():
                raise CustomerAlreadyExistsError(str(e), self.system_name, e.code)
            elif "No such customer" in str(e):
                raise CustomerNotFoundError(str(e), self.system_name)
            raise IntegrationError(str(e), self.system_name)
        except stripe.error.RateLimitError as e:
            raise RateLimitError(str(e), self.system_name)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(str(e), self.system_name)
        except Exception as e:
            logger.error(f"Stripe operation failed: {e}")
            raise IntegrationError(str(e), self.system_name)
            
    async def create_customer(self, customer_data: Dict[str, Any]) -> str:
        """Create a customer in Stripe."""
        transformed_data = self.transform_internal_to_external(customer_data)
        customer = await self._run_stripe_operation(
            lambda: stripe.Customer.create(**transformed_data)
        )
        logger.info(f"Created Stripe customer: {customer.id}")
        return customer.id

    async def update_customer(self, external_id: str, customer_data: Dict[str, Any]) -> None:
        """Update a customer in Stripe."""
        transformed_data = self.transform_internal_to_external(customer_data)
        await self._run_stripe_operation(
            lambda: stripe.Customer.modify(external_id, **transformed_data)
        )
        logger.info(f"Updated Stripe customer: {external_id}")

    async def delete_customer(self, external_id: str) -> bool:
        """Delete a customer in Stripe."""
        try:
            await self._run_stripe_operation(
                lambda: stripe.Customer.delete(external_id)
            )
            logger.info(f"Deleted Stripe customer: {external_id}")
            return True
        except CustomerNotFoundError:
            logger.warning(f"Customer {external_id} not found for deletion.")
            return True  # Already deleted
            
    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get a customer from Stripe."""
        try:
            customer = await self._run_stripe_operation(
                lambda: stripe.Customer.retrieve(external_id)
            )
            return self.transform_external_to_internal(customer)
        except CustomerNotFoundError:
            return None
            
    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List customers from Stripe."""
        try:
            result = await self._run_stripe_operation(
                lambda: stripe.Customer.list(limit=min(limit, 100), starting_after=None if offset == 0 else offset)
            )
            return [self.transform_external_to_internal(cust) for cust in result.data]
        except Exception as e:
            logger.error(f"Failed to list customers from Stripe: {e}")
            raise IntegrationError(str(e), self.system_name)

    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate Stripe webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header (from 'Stripe-Signature')
            
        Returns:
            True if signature is valid
        """
        try:
            await self._run_stripe_operation(
                lambda: stripe.Webhook.construct_event(
                    payload=payload,
                    sig_header=signature,
                    secret=self.webhook_secret
                )
            )
            return True
        except (stripe.error.SignatureVerificationError, ValueError) as e:
            logger.warning(f"Invalid Stripe webhook signature: {e}")
            return False

    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature from Stripe.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            True if signature is valid
        """
        try:
            stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
            return True
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe signature")
            return False
        except Exception as e:
            logger.error(f"Failed to verify webhook: {e}")
            return False
