"""
Configuration module for the MCP Context Service
Implements security-first configuration with environment variable support
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import logging

class SecuritySettings(BaseSettings):
    """Security-related configuration"""
    
    # JWT Configuration with JWKS support
    secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")  # Fallback for local dev
    algorithm: str = Field(default="RS256", env="JWT_ALGORITHM")  # Changed to RS256 for JWKS
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Auth Service Configuration
    auth_service_url: str = Field(default="http://auth-service:8080", env="AUTH_SERVICE_URL")
    jwks_cache_ttl: int = Field(default=3600, env="JWKS_CACHE_TTL")  # seconds
    
    # TLS Configuration
    enable_tls: bool = Field(default=True, env="ENABLE_TLS")
    enable_mutual_tls: bool = Field(default=True, env="ENABLE_MUTUAL_TLS")
    tls_certs_dir: str = Field(default="/etc/certs", env="TLS_CERTS_DIR")
    
    # Header Validation
    require_tenant_id: bool = Field(default=True, env="REQUIRE_TENANT_ID")
    require_request_id: bool = Field(default=True, env="REQUIRE_REQUEST_ID")
    auto_generate_request_id: bool = Field(default=True, env="AUTO_GENERATE_REQUEST_ID")
    
    # API Rate Limiting
    rate_limit_calls: int = Field(default=100, env="RATE_LIMIT_CALLS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # CORS Settings
    allowed_origins: List[str] = Field(default=["https://localhost:3000"], env="ALLOWED_ORIGINS")
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT"], env="ALLOWED_METHODS")
    
    # Input validation
    max_context_data_size: int = Field(default=1048576, env="MAX_CONTEXT_DATA_SIZE")  # 1MB in bytes
    max_tags_count: int = Field(default=20, env="MAX_TAGS_COUNT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    
    # PostgreSQL Configuration
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="context_service", env="DB_NAME")
    db_user: str = Field(default="context_user", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Connection settings
    db_timeout: int = Field(default=30, env="DB_TIMEOUT")  # seconds
    db_ssl_mode: str = Field(default="prefer", env="DB_SSL_MODE")
    
    # Redis Configuration (for future caching)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, env="REDIS_CACHE_TTL")  # seconds
    
    def get_database_url(self) -> str:
        """Generate PostgreSQL URL from components"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class ServiceSettings(BaseSettings):
    """General service configuration"""
    
    # Service Identity
    service_name: str = Field(default="mcp-context-service", env="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")  # Different port from summarization service
    debug: bool = Field(default=False, env="DEBUG")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Health check configuration
    health_check_timeout: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")
    
    # Metrics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9091, env="METRICS_PORT")  # Different port from summarization service
    
    # OpenTelemetry Configuration
    enable_telemetry: bool = Field(default=True, env="ENABLE_TELEMETRY")
    otel_exporter_otlp_endpoint: str = Field(default="http://otel-collector:4317", env="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_enable_console: bool = Field(default=False, env="OTEL_ENABLE_CONSOLE")
    otel_trace_sample_rate: float = Field(default=1.0, env="OTEL_TRACE_SAMPLE_RATE")
    otel_metrics_export_interval: int = Field(default=30, env="OTEL_METRICS_EXPORT_INTERVAL")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of {allowed_envs}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of {allowed_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class ContextSettings(BaseSettings):
    """Context-specific configuration"""
    
    # Context storage settings
    default_context_ttl: int = Field(default=86400 * 30, env="DEFAULT_CONTEXT_TTL")  # 30 days in seconds
    max_context_ttl: int = Field(default=86400 * 365, env="MAX_CONTEXT_TTL")  # 1 year in seconds
    
    # Context validation
    allowed_context_types: List[str] = Field(
        default=[
            "user_preferences", 
            "session_data", 
            "application_state", 
            "user_profile", 
            "configuration"
        ], 
        env="ALLOWED_CONTEXT_TYPES"
    )
    
    # Cleanup settings
    enable_automatic_cleanup: bool = Field(default=True, env="ENABLE_AUTOMATIC_CLEANUP")
    cleanup_interval_hours: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    
    # Search and indexing
    enable_full_text_search: bool = Field(default=False, env="ENABLE_FULL_TEXT_SEARCH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class Settings:
    """Main settings class that combines all configuration sections"""
    
    def __init__(self):
        self.security = SecuritySettings()
        self.database = DatabaseSettings()
        self.service = ServiceSettings()
        self.context = ContextSettings()
        
        # Configure logging based on settings
        self._configure_logging()
        
        # Validate configuration
        self._validate_configuration()
    
    def _configure_logging(self):
        """Configure logging based on service settings"""
        
        log_level = getattr(logging, self.service.log_level)
        
        if self.service.log_format == "json":
            import structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        else:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _validate_configuration(self):
        """Validate the complete configuration"""
        
        # Check database configuration
        if not self.database.db_password and self.service.environment == "production":
            logging.warning("Database password not set in production environment")
        
        # Security validation
        if self.service.environment == "production":
            if self.service.debug:
                logging.warning("Debug mode enabled in production environment")
            
            if self.security.secret_key and len(self.security.secret_key) < 32:
                raise ValueError("JWT secret key must be at least 32 characters in production")
        
        # Context type validation
        if not self.context.allowed_context_types:
            raise ValueError("At least one context type must be allowed")
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.service.environment == "production"
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.database.get_database_url()

# Global settings instance
settings = Settings()

# Export settings for easy import
__all__ = ["settings", "Settings", "SecuritySettings", "DatabaseSettings", "ServiceSettings", "ContextSettings"]
