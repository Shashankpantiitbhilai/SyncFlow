"""
Base integration interface for external systems.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseIntegration(ABC):
    """Base class for all external system integrations."""
    
    def __init__(self, system_name: str):
        self.system_name = system_name
    
    @abstractmethod
    async def create_customer(self, customer_data: Dict[str, Any]) -> str:
        """
        Create a customer in the external system.
        
        Args:
            customer_data: Customer data including name, email, etc.
            
        Returns:
            External system customer ID
        """
        pass
    
    @abstractmethod
    async def update_customer(self, external_id: str, customer_data: Dict[str, Any]) -> bool:
        """
        Update a customer in the external system.
        
        Args:
            external_id: External system customer ID
            customer_data: Updated customer data
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def delete_customer(self, external_id: str) -> bool:
        """
        Delete a customer in the external system.
        
        Args:
            external_id: External system customer ID
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a customer from the external system.
        
        Args:
            external_id: External system customer ID
            
        Returns:
            Customer data or None if not found
        """
        pass
    
    @abstractmethod
    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List customers from the external system.
        
        Args:
            limit: Maximum number of customers to return
            offset: Number of customers to skip
            
        Returns:
            List of customer data
        """
        pass
    
    @abstractmethod
    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature from the external system.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            
        Returns:
            True if signature is valid
        """
        pass
    
    def transform_internal_to_external(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform internal customer data to external system format.
        
        Args:
            customer_data: Internal customer data
            
        Returns:
            Transformed data for external system
        """
        # Default implementation - can be overridden by specific integrations
        return {
            "name": customer_data.get("name"),
            "email": customer_data.get("email")
        }
    
    def transform_external_to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform external system data to internal format.
        
        Args:
            external_data: External system customer data
            
        Returns:
            Transformed data for internal system
        """
        # Default implementation - can be overridden by specific integrations
        return {
            "name": external_data.get("name"),
            "email": external_data.get("email")
        }


class IntegrationError(Exception):
    """Base exception for integration errors."""
    
    def __init__(self, message: str, system: str, error_code: Optional[str] = None):
        self.message = message
        self.system = system
        self.error_code = error_code
        super().__init__(self.message)


class CustomerNotFoundError(IntegrationError):
    """Exception raised when customer is not found in external system."""
    pass


class CustomerAlreadyExistsError(IntegrationError):
    """Exception raised when customer already exists in external system."""
    pass


class RateLimitError(IntegrationError):
    """Exception raised when rate limit is exceeded."""
    pass


class AuthenticationError(IntegrationError):
    """Exception raised when authentication fails."""
    pass
