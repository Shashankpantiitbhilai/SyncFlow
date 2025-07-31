"""
Kafka client for producing and consuming messages.
"""
import json
import logging
from typing import Any, Dict, Optional, Callable
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .config import settings

logger = logging.getLogger(__name__)


class KafkaClient:
    """Kafka client for message production and consumption."""
    
    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
    
    async def start_producer(self) -> None:
        """Start the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop_producer(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def produce_message(
        self, 
        topic: str, 
        message: Dict[str, Any], 
        key: Optional[str] = None
    ) -> None:
        """Produce a message to a Kafka topic."""
        if not self.producer:
            await self.start_producer()
        
        try:
            await self.producer.send_and_wait(topic, message, key=key)
            logger.info(f"Message sent to topic {topic}: {message}")
        except KafkaError as e:
            logger.error(f"Failed to send message to topic {topic}: {e}")
            raise
    
    async def start_consumer(
        self, 
        topic: str, 
        group_id: Optional[str] = None,
        message_handler: Optional[Callable] = None
    ) -> AIOKafkaConsumer:
        """Start a Kafka consumer for a specific topic."""
        consumer_group = group_id or settings.kafka_group_id
        
        try:
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=consumer_group,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                session_timeout_ms=60000,  # 60 seconds
                heartbeat_interval_ms=20000,  # 20 seconds
                max_poll_interval_ms=300000,  # 5 minutes
                enable_auto_commit=True,
                auto_commit_interval_ms=5000  # 5 seconds
            )
            
            # Wait for topics to be available
            await consumer.start()
            await consumer._client.force_metadata_update()  # Force metadata update
            self.consumers[topic] = consumer
            
            logger.info(f"Kafka consumer started for topic {topic} with group {consumer_group}")
            
            if message_handler:
                await self._consume_messages(consumer, message_handler)
            
            return consumer
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer for topic {topic}: {e}")
            raise
    
    async def _consume_messages(
        self, 
        consumer: AIOKafkaConsumer, 
        message_handler: Callable
    ) -> None:
        """Consume messages from Kafka and process them."""
        try:
            async for message in consumer:
                try:
                    await message_handler(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # In a production system, you might want to send failed messages
                    # to a dead letter queue here
        except Exception as e:
            logger.error(f"Error in message consumption: {e}")
            raise
    
    async def stop_consumer(self, topic: str) -> None:
        """Stop a Kafka consumer for a specific topic."""
        if topic in self.consumers:
            await self.consumers[topic].stop()
            del self.consumers[topic]
            logger.info(f"Kafka consumer stopped for topic {topic}")
    
    async def stop_all_consumers(self) -> None:
        """Stop all Kafka consumers."""
        for topic in list(self.consumers.keys()):
            await self.stop_consumer(topic)
    
    async def close(self) -> None:
        """Close all Kafka connections."""
        await self.stop_producer()
        await self.stop_all_consumers()


# Global Kafka client instance
kafka_client = KafkaClient()


# Kafka topic names
class KafkaTopics:
    SYNC_OUTBOUND = "sync.outbound"
    SYNC_INBOUND = "sync.inbound"
