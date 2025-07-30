"""
Base worker class for background processing.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from aiokafka import AIOKafkaConsumer

from ..core import kafka_client, settings

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for all background workers."""
    
    def __init__(self, worker_name: str):
        self.worker_name = worker_name
        self.running = False
        self.consumer: AIOKafkaConsumer = None
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message from the queue."""
        pass
    
    @abstractmethod
    def get_topic(self) -> str:
        """Get the Kafka topic this worker should consume from."""
        pass
    
    async def start(self) -> None:
        """Start the worker."""
        logger.info(f"Starting worker: {self.worker_name}")
        self.running = True
        
        try:
            # Start Kafka consumer
            self.consumer = await kafka_client.start_consumer(
                self.get_topic(),
                group_id=f"{settings.kafka_group_id}-{self.worker_name}",
                message_handler=self._handle_message
            )
            
            logger.info(f"Worker {self.worker_name} started successfully")
            
            # Keep the worker running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Worker {self.worker_name} failed: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the worker."""
        logger.info(f"Stopping worker: {self.worker_name}")
        self.running = False
        
        if self.consumer:
            await kafka_client.stop_consumer(self.get_topic())
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a message from Kafka."""
        try:
            logger.info(f"Processing message in {self.worker_name}: {message}")
            await self.process_message(message)
            logger.info(f"Message processed successfully by {self.worker_name}")
        except Exception as e:
            logger.error(f"Failed to process message in {self.worker_name}: {e}")
            # In a production system, you might want to:
            # 1. Send to dead letter queue
            # 2. Implement retry logic
            # 3. Alert monitoring systems
