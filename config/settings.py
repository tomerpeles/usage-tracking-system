from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class DatabaseSettings(BaseSettings):
    host: str = Field(default="localhost", alias="DATABASE_HOST")
    port: int = Field(default=5432, alias="DATABASE_PORT")
    name: str = Field(default="usage_tracking", alias="DATABASE_NAME")
    user: str = Field(default="username", alias="DATABASE_USER")
    password: str = Field(default="password", alias="DATABASE_PASSWORD")
    url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    @property
    def database_url(self) -> str:
        if self.url:
            return self.url
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    url: Optional[str] = Field(default=None, alias="REDIS_URL")
    
    @property
    def redis_url(self) -> str:
        if self.url:
            return self.url
        return f"redis://{self.host}:{self.port}/{self.db}"


class APISettings(BaseSettings):
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    secret_key: str = Field(default="dev-secret-key", alias="API_SECRET_KEY")
    
    # Service ports
    api_gateway_port: int = Field(default=8000, alias="API_GATEWAY_PORT")
    event_processor_port: int = Field(default=8001, alias="EVENT_PROCESSOR_PORT")
    query_service_port: int = Field(default=8002, alias="QUERY_SERVICE_PORT")
    aggregation_service_port: int = Field(default=8003, alias="AGGREGATION_SERVICE_PORT")


class LoggingSettings(BaseSettings):
    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="json", alias="LOG_FORMAT")


class RateLimitSettings(BaseSettings):
    per_minute: int = Field(default=1000, alias="RATE_LIMIT_PER_MINUTE")
    burst: int = Field(default=100, alias="RATE_LIMIT_BURST")


class RetentionSettings(BaseSettings):
    event_retention_days: int = Field(default=365, alias="EVENT_RETENTION_DAYS")
    aggregate_retention_days: int = Field(default=1095, alias="AGGREGATE_RETENTION_DAYS")


class BatchSettings(BaseSettings):
    max_batch_size: int = Field(default=1000, alias="MAX_BATCH_SIZE")
    timeout_seconds: int = Field(default=30, alias="BATCH_TIMEOUT_SECONDS")


class AlertSettings(BaseSettings):
    error_rate_threshold: float = Field(default=0.05, alias="ALERT_ERROR_RATE_THRESHOLD")
    latency_threshold_ms: int = Field(default=1000, alias="ALERT_LATENCY_THRESHOLD_MS")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    batch: BatchSettings = Field(default_factory=BatchSettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)


# Global settings instance
settings = Settings()