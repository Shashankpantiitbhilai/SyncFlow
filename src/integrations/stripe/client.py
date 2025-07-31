import asyncio
import logging
from typing import Dict, Any, Optional, List
import stripe

from ...core import settings
from ..base import (
    BaseIntegration,
    IntegrationError,
    CustomerNotFoundError,
    CustomerAlreadyExistsError,
    RateLimitError,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class StripeIntegration(BaseIntegration):
    """Stripe integration for customer synchronization."""

    def __init__(self):
        super().__init__("stripe")
        # Ensure secrets are set
        if not settings.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is not set")
        if not settings.stripe_webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET environment variable is not set")

        # Log and validate Stripe settings
        if not isinstance(settings.stripe_secret_key, str):
            raise ValueError("STRIPE_SECRET_KEY must be a string")
        if not isinstance(settings.stripe_webhook_secret, str):
            raise ValueError("STRIPE_WEBHOOK_SECRET must be a string")

        logger.info(f"Raw Stripe Secret Key: {settings.stripe_secret_key}")
        logger.info(f"Raw Stripe Webhook Secret: {settings.stripe_webhook_secret}")
        
        # Store the keys
        self.api_key = settings.stripe_secret_key
        self.webhook_secret = settings.stripe_webhook_secret
        
        # Configure stripe library
        stripe.api_key = self.api_key
        stripe.api_version = settings.stripe_api_version
        
        # Verify API key works
        try:
            stripe.Customer.list(limit=1)
            logger.info("Successfully connected to Stripe API")
        except stripe.error.AuthenticationError as e:
            logger.error(f"Failed to authenticate with Stripe: {e}")
            raise
        
        # Log the processed keys
        logger.info(f"Processed Stripe Secret Key: {self.api_key}")
        logger.info(f"Processed Stripe Webhook Secret: {self.webhook_secret}")

        stripe.api_key = self.api_key
        stripe.api_version = settings.stripe_api_version

    def transform_internal_to_external(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        stripe_data: Dict[str, Any] = {}
        if "name" in customer_data:
            stripe_data["name"] = customer_data["name"]
        if "email" in customer_data:
            stripe_data["email"] = customer_data["email"]
        stripe_data["metadata"] = {"internal_id": str(customer_data.get("id", ""))}
        return stripe_data

    def transform_external_to_internal(self, stripe_customer) -> Dict[str, Any]:
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
        try:
            return operation()
        except stripe.error.InvalidRequestError as e:
            msg = str(e).lower()
            if "already exists" in msg:
                raise CustomerAlreadyExistsError(str(e), self.system_name, e.code)
            if "no such customer" in str(e).lower():
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
        transformed_data = self.transform_internal_to_external(customer_data)
        logger.info(f"Creating Stripe customer with data: {transformed_data}")
        customer = await self._run_stripe_operation(
            lambda: stripe.Customer.create(**transformed_data)
        )
        if not customer or not customer.id:
            logger.error("Failed to create customer in Stripe or no ID received")
            raise IntegrationError("No customer ID received from Stripe", self.system_name)
        
        logger.info(f"Created Stripe customer: {customer.id}")
        logger.info(f"Full Stripe response: {customer}")
        return customer.id

    async def update_customer(self, external_id: str, customer_data: Dict[str, Any]) -> None:
        transformed_data = self.transform_internal_to_external(customer_data)
        await self._run_stripe_operation(
            lambda: stripe.Customer.modify(external_id, **transformed_data)
        )
        logger.info(f"Updated Stripe customer: {external_id}")

    async def delete_customer(self, external_id: str) -> bool:
        try:
            await self._run_stripe_operation(
                lambda: stripe.Customer.delete(external_id)
            )
            logger.info(f"Deleted Stripe customer: {external_id}")
            return True
        except CustomerNotFoundError:
            logger.warning(f"Customer {external_id} not found for deletion.")
            return True

    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        try:
            customer = await self._run_stripe_operation(
                lambda: stripe.Customer.retrieve(external_id)
            )
            return self.transform_external_to_internal(customer)
        except CustomerNotFoundError:
            return None

    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            result = await self._run_stripe_operation(
                lambda: stripe.Customer.list(
                    limit=min(limit, 100), starting_after=None if offset == 0 else offset
                )
            )
            return [self.transform_external_to_internal(c) for c in result.data]
        except Exception as e:
            logger.error(f"Failed to list customers from Stripe: {e}")
            raise IntegrationError(str(e), self.system_name)

    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature from Stripe.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            True if signature is valid, else False.
        """
        try:
            logger.info("Validating webhook signature")
            logger.info(f"Webhook Secret being used: {self.webhook_secret}")
            result = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self.webhook_secret
            )
            logger.info("Webhook signature validation successful")
            return True
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe signature: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to verify webhook: {e}")
            return False
