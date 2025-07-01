"""
Configuration module for the MCP Text Summarization Service
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
    allowed_methods: List[str] = Field(default=["GET", "POST"], env="ALLOWED_METHODS")
    
    # Input validation
    max_text_length: int = Field(default=50000, env="MAX_TEXT_LENGTH")  # characters
    min_text_length: int = Field(default=100, env="MIN_TEXT_LENGTH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class AIModelSettings(BaseSettings):
    """AI Model configuration"""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    
    # Hugging Face Configuration
    hf_model_name: str = Field(default="facebook/bart-large-cnn", env="HF_MODEL_NAME")
    hf_api_token: Optional[str] = Field(default=None, env="HF_API_TOKEN")
    
    # Sentence Transformer for semantic evaluation
    sentence_transformer_model: str = Field(
        default="all-MiniLM-L6-v2", 
        env="SENTENCE_TRANSFORMER_MODEL"
    )
    
    # Summarization parameters
    default_summary_ratio: float = Field(default=0.3, env="DEFAULT_SUMMARY_RATIO")
    min_summary_length: int = Field(default=50, env="MIN_SUMMARY_LENGTH")
    max_summary_length: int = Field(default=500, env="MAX_SUMMARY_LENGTH")
    
    # Semantic evaluation
    default_semantic_threshold: float = Field(default=0.8, env="DEFAULT_SEMANTIC_THRESHOLD")
    min_semantic_threshold: float = Field(default=0.6, env="MIN_SEMANTIC_THRESHOLD")
    max_semantic_threshold: float = Field(default=0.95, env="MAX_SEMANTIC_THRESHOLD")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    
    @validator('default_semantic_threshold', 'min_semantic_threshold', 'max_semantic_threshold')
    def validate_threshold_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Semantic threshold must be between 0.0 and 1.0')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class ServiceSettings(BaseSettings):
    """General service configuration"""
    
    # Service Identity
    service_name: str = Field(default="mcp-text-summarization", env="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Health check configuration
    health_check_timeout: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")
    
    # Metrics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
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

class Settings:
    """Main settings class that combines all configuration sections"""
    
    def __init__(self):
        self.security = SecuritySettings()
        self.ai_models = AIModelSettings()
        self.service = ServiceSettings()
        
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
        
        # Check if at least one AI model is configured
        if not self.ai_models.openai_api_key and not self.ai_models.hf_api_token:
            logging.warning(
                "No AI model API keys configured. Service will use local models only."
            )
        
        # Validate semantic threshold ranges
        if self.ai_models.min_semantic_threshold >= self.ai_models.max_semantic_threshold:
            raise ValueError(
                "min_semantic_threshold must be less than max_semantic_threshold"
            )
        
        # Security validation
        if self.service.environment == "production":
            if self.service.debug:
                logging.warning("Debug mode enabled in production environment")
            
            if len(self.security.secret_key) < 32:
                raise ValueError("JWT secret key must be at least 32 characters in production")
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.service.environment == "production"
    
    def get_model_config(self, model_type: str = "openai") -> dict:
        """Get configuration for specified model type"""
        
        if model_type == "openai":
            return {
                "api_key": self.ai_models.openai_api_key,
                "model": self.ai_models.openai_model,
                "max_tokens": self.ai_models.openai_max_tokens
            }
        elif model_type == "huggingface":
            return {
                "model_name": self.ai_models.hf_model_name,
                "api_token": self.ai_models.hf_api_token
            }
        else:
            raise ValueError(f"Unknown model type: {model_type}")

# Global settings instance
settings = Settings()

# Export settings for easy import
__all__ = ["settings", "Settings", "SecuritySettings", "AIModelSettings", "ServiceSettings"]
