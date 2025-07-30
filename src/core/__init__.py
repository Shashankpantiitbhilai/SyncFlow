"""
Core package initialization.
"""
from .config import settings
from .database import get_db, engine, AsyncSessionLocal
from .kafka_client import kafka_client, KafkaTopics

__all__ = [
    "settings",
    "get_db", 
    "engine",
    "AsyncSessionLocal",
    "kafka_client",
    "KafkaTopics",
]
