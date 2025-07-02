"""
Enhanced structured logging configuration for the MCP Text Summarization Service.

Integrates structlog with OpenTelemetry for consistent JSON logs with trace correlation.
"""

import logging
import logging.config
import sys
from typing import Any, Dict, Optional
import structlog
from opentelemetry import trace
from config import settings


class OpenTelemetryProcessor:
    """Structlog processor that adds OpenTelemetry trace information to log records."""
    
    def __call__(self, logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add OpenTelemetry trace information to the log event."""
        
        # Get current span context
        span = trace.get_current_span()
        if span.is_recording():
            span_context = span.get_span_context()
            
            # Add trace information
            event_dict["trace_id"] = format(span_context.trace_id, "032x")
            event_dict["span_id"] = format(span_context.span_id, "016x")
            
            # Add trace flags if available
            if span_context.trace_flags:
                event_dict["trace_flags"] = f"{span_context.trace_flags:02x}"
        
        return event_dict


class ServiceContextProcessor:
    """Add consistent service context to all log records."""
    
    def __call__(self, logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add service context information."""
        
        event_dict.update({
            "service": {
                "name": settings.service.service_name,
                "version": settings.service.service_version,
                "environment": settings.service.environment
            }
        })
        
        return event_dict


def setup_structured_logging():
    """
    Configure structured logging with JSON output and OpenTelemetry integration.
    
    This function sets up:
    - JSON-formatted log output
    - OpenTelemetry trace correlation
    - Service context in all logs
    - Appropriate log levels and processors
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.service.log_level)
    )
    
    # Configure structlog processors
    processors = [
        # Filter by log level
        structlog.stdlib.filter_by_level,
        
        # Add logger name
        structlog.stdlib.add_logger_name,
        
        # Add log level
        structlog.stdlib.add_log_level,
        
        # Add service context
        ServiceContextProcessor(),
        
        # Add OpenTelemetry trace information
        OpenTelemetryProcessor(),
        
        # Handle positional arguments
        structlog.stdlib.PositionalArgumentsFormatter(),
        
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        
        # Format exception info
        structlog.processors.format_exc_info,
        
        # Ensure unicode
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on environment
    if settings.service.environment == "development" and settings.service.debug:
        # Use colored console output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Use JSON for production/staging
        processors.append(structlog.processors.JSONRenderer(sort_keys=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.INFO)
    
    # Create a test log entry
    logger = structlog.get_logger(__name__)
    logger.info(
        "Structured logging configured",
        log_level=settings.service.log_level,
        log_format="json" if not settings.service.debug else "console",
        processors_count=len(processors)
    )


def get_logger(name: str, **initial_values) -> structlog.BoundLogger:
    """
    Get a structured logger with optional initial context values.
    
    Args:
        name: Logger name (typically __name__)
        **initial_values: Initial context values to bind to the logger
        
    Returns:
        Configured structlog.BoundLogger instance
    """
    logger = structlog.get_logger(name)
    
    if initial_values:
        logger = logger.bind(**initial_values)
    
    return logger


def log_request_context(
    request_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a consistent request context dictionary for logging.
    
    Args:
        request_id: Unique request identifier
        tenant_id: Tenant identifier
        user_id: User identifier
        correlation_id: Correlation identifier for tracing across services
        
    Returns:
        Dictionary with request context for logging
    """
    context = {}
    
    if request_id:
        context["request_id"] = request_id
    if tenant_id:
        context["tenant_id"] = tenant_id
    if user_id:
        context["user_id"] = user_id
    if correlation_id:
        context["correlation_id"] = correlation_id
        
    return context


def log_performance_metrics(
    operation: str,
    duration_ms: float,
    status: str = "success",
    **additional_metrics
) -> Dict[str, Any]:
    """
    Create a structured performance metrics dictionary.
    
    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        status: Operation status (success, error, timeout, etc.)
        **additional_metrics: Additional metrics to include
        
    Returns:
        Dictionary with performance metrics for logging
    """
    metrics = {
        "performance": {
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "status": status
        }
    }
    
    if additional_metrics:
        metrics["performance"].update(additional_metrics)
    
    return metrics


def log_error_context(
    error: Exception,
    error_code: Optional[str] = None,
    user_message: Optional[str] = None,
    **additional_context
) -> Dict[str, Any]:
    """
    Create a structured error context dictionary.
    
    Args:
        error: The exception that occurred
        error_code: Optional error code for categorization
        user_message: User-friendly error message
        **additional_context: Additional error context
        
    Returns:
        Dictionary with error context for logging
    """
    error_context = {
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        }
    }
    
    if error_code:
        error_context["error"]["code"] = error_code
    if user_message:
        error_context["error"]["user_message"] = user_message
    
    if additional_context:
        error_context["error"].update(additional_context)
    
    return error_context


def log_business_event(
    event_type: str,
    event_name: str,
    **event_data
) -> Dict[str, Any]:
    """
    Create a structured business event dictionary.
    
    Args:
        event_type: Type/category of the business event
        event_name: Specific name of the event
        **event_data: Additional event data
        
    Returns:
        Dictionary with business event data for logging
    """
    event = {
        "business_event": {
            "type": event_type,
            "name": event_name
        }
    }
    
    if event_data:
        event["business_event"]["data"] = event_data
    
    return event


# Common logger instances for different use cases
security_logger = get_logger("security")
performance_logger = get_logger("performance")
business_logger = get_logger("business")
audit_logger = get_logger("audit")


def log_security_event(
    event_type: str,
    event_details: Dict[str, Any],
    severity: str = "info",
    **context
):
    """
    Log a security-related event with consistent formatting.
    
    Args:
        event_type: Type of security event (auth, access, violation, etc.)
        event_details: Details about the security event
        severity: Severity level (info, warning, error, critical)
        **context: Additional context (request_id, user_id, etc.)
    """
    log_data = {
        "security_event": {
            "type": event_type,
            "severity": severity,
            "details": event_details
        }
    }
    
    if context:
        log_data.update(context)
    
    # Log at appropriate level based on severity
    if severity == "critical":
        security_logger.critical("Security event", **log_data)
    elif severity == "error":
        security_logger.error("Security event", **log_data)
    elif severity == "warning":
        security_logger.warning("Security event", **log_data)
    else:
        security_logger.info("Security event", **log_data)


def log_audit_event(
    action: str,
    resource: str,
    outcome: str,
    actor: Optional[str] = None,
    **details
):
    """
    Log an audit event with consistent formatting.
    
    Args:
        action: Action performed (create, read, update, delete, etc.)
        resource: Resource that was acted upon
        outcome: Outcome of the action (success, failure, denied)
        actor: Who performed the action
        **details: Additional audit details
    """
    audit_data = {
        "audit_event": {
            "action": action,
            "resource": resource,
            "outcome": outcome
        }
    }
    
    if actor:
        audit_data["audit_event"]["actor"] = actor
    
    if details:
        audit_data["audit_event"]["details"] = details
    
    audit_logger.info("Audit event", **audit_data)
