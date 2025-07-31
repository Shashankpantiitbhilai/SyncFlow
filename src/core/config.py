# src/core/settings.py

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 0

    # Kafka
    kafka_bootstrap_servers: str
    kafka_group_id: str = "zenskar-sync"
    kafka_auto_offset_reset: str = "earliest"

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_api_version: str = "2023-10-16"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    secret_key: str = "zenskar-backend"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Webhook
    webhook_base_url: Optional[str] = None

    # Environment
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""
        use_enum_values = True
        env_prefix = ""
        use_enum_values = True


settings = Settings()
