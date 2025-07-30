"""
Integrations package initialization.
"""
from .base import BaseIntegration, IntegrationError
from .stripe import StripeIntegration

__all__ = [
    "BaseIntegration",
    "IntegrationError", 
    "StripeIntegration",
]
