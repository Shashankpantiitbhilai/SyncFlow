"""
Stripe API client for customer management.
"""
import logging
from typing import Dict, Any, Optional, List
import stripe
import hmac
import hashlib

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
        stripe.api_key = settings.stripe_secret_key
        stripe.api_version = settings.stripe_api_version
        self.webhook_secret = settings.stripe_webhook_secret
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> str:
        """Create a customer in Stripe."""
        try:
            transformed_data = self.transform_internal_to_external(customer_data)
            
            customer = stripe.Customer.create(**transformed_data)
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer.id
            
        except stripe.error.InvalidRequestError as e:
            if "already exists" in str(e).lower():
                raise CustomerAlreadyExistsError(
                    f"Customer with email {customer_data.get('email')} already exists in Stripe",
                    "stripe",
                    e.code
                )
            raise IntegrationError(f"Invalid request: {e}", "stripe", e.code)
        except stripe.error.RateLimitError as e:
            raise RateLimitError(f"Stripe rate limit exceeded: {e}", "stripe", e.code)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(f"Stripe authentication failed: {e}", "stripe", e.code)
        except Exception as e:
            logger.error(f"Failed to create customer in Stripe: {e}")
            raise IntegrationError(f"Failed to create customer: {e}", "stripe")
    
    async def update_customer(self, external_id: str, customer_data: Dict[str, Any]) -> bool:
        """Update a customer in Stripe."""
        try:
            transformed_data = self.transform_internal_to_external(customer_data)
            
            stripe.Customer.modify(external_id, **transformed_data)
            logger.info(f"Updated Stripe customer: {external_id}")
            return True
            
        except stripe.error.InvalidRequestError as e:
            if "No such customer" in str(e):
                raise CustomerNotFoundError(
                    f"Customer {external_id} not found in Stripe",
                    "stripe",
                    e.code
                )
            raise IntegrationError(f"Invalid request: {e}", "stripe", e.code)
        except stripe.error.RateLimitError as e:
            raise RateLimitError(f"Stripe rate limit exceeded: {e}", "stripe", e.code)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(f"Stripe authentication failed: {e}", "stripe", e.code)
        except Exception as e:
            logger.error(f"Failed to update customer in Stripe: {e}")
            raise IntegrationError(f"Failed to update customer: {e}", "stripe")
    
    async def delete_customer(self, external_id: str) -> bool:
        """Delete a customer in Stripe."""
        try:
            stripe.Customer.delete(external_id)
            logger.info(f"Deleted Stripe customer: {external_id}")
            return True
            
        except stripe.error.InvalidRequestError as e:
            if "No such customer" in str(e):
                logger.warning(f"Customer {external_id} not found in Stripe for deletion")
                return True  # Consider it successful if already deleted
            raise IntegrationError(f"Invalid request: {e}", "stripe", e.code)
        except stripe.error.RateLimitError as e:
            raise RateLimitError(f"Stripe rate limit exceeded: {e}", "stripe", e.code)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(f"Stripe authentication failed: {e}", "stripe", e.code)
        except Exception as e:
            logger.error(f"Failed to delete customer in Stripe: {e}")
            raise IntegrationError(f"Failed to delete customer: {e}", "stripe")
    
    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get a customer from Stripe."""
        try:
            customer = stripe.Customer.retrieve(external_id)
            return self.transform_external_to_internal(customer)
            
        except stripe.error.InvalidRequestError as e:
            if "No such customer" in str(e):
                return None
            raise IntegrationError(f"Invalid request: {e}", "stripe", e.code)
        except stripe.error.RateLimitError as e:
            raise RateLimitError(f"Stripe rate limit exceeded: {e}", "stripe", e.code)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(f"Stripe authentication failed: {e}", "stripe", e.code)
        except Exception as e:
            logger.error(f"Failed to get customer from Stripe: {e}")
            raise IntegrationError(f"Failed to get customer: {e}", "stripe")
    
    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List customers from Stripe."""
        try:
            customers = stripe.Customer.list(
                limit=min(limit, 100),  # Stripe max is 100
                starting_after=None if offset == 0 else str(offset)
            )
            
            return [
                self.transform_external_to_internal(customer) 
                for customer in customers.data
            ]
            
        except stripe.error.RateLimitError as e:
            raise RateLimitError(f"Stripe rate limit exceeded: {e}", "stripe", e.code)
        except stripe.error.AuthenticationError as e:
            raise AuthenticationError(f"Stripe authentication failed: {e}", "stripe", e.code)
        except Exception as e:
            logger.error(f"Failed to list customers from Stripe: {e}")
            raise IntegrationError(f"Failed to list customers: {e}", "stripe")
    
    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Validate Stripe webhook signature."""
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except ValueError:
            logger.error("Invalid payload")
            return False
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            return False
        except Exception as e:
            logger.error(f"Webhook signature validation failed: {e}")
            return False
    
    def transform_internal_to_external(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform internal customer data to Stripe format."""
        stripe_data = {}
        
        if "name" in customer_data:
            stripe_data["name"] = customer_data["name"]
        
        if "email" in customer_data:
            stripe_data["email"] = customer_data["email"]
        
        # Add any additional Stripe-specific fields here
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
                "metadata": stripe_customer.metadata
            }
        }
