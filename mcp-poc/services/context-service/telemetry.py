"""
OpenTelemetry integration for the MCP Text Summarization Service.

Provides distributed tracing, metrics collection, and observability
with integration to in-cluster OTel collector.
"""

import os
import logging
from typing import Optional, Dict, Any

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
import structlog

from config import settings

logger = structlog.get_logger(__name__)

class TelemetryConfig:
    """Configuration for OpenTelemetry setup"""
    
    def __init__(self):
        # Service identity
        self.service_name = settings.service.service_name
        self.service_version = settings.service.service_version
        self.environment = settings.service.environment
        
        # OTel Collector endpoint
        self.otel_endpoint = settings.service.otel_exporter_otlp_endpoint
        
        # Additional configuration
        self.enable_console_export = settings.service.otel_enable_console
        self.trace_sample_rate = settings.service.otel_trace_sample_rate
        self.metrics_export_interval = settings.service.otel_metrics_export_interval
        
        # Custom attributes
        self.resource_attributes = {
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "service.environment": self.environment,
            "service.team": "mcp-team",
            "service.component": "text-summarization",
        }
        
        logger.info(
            "Telemetry configuration initialized",
            service_name=self.service_name,
            service_version=self.service_version,
            environment=self.environment,
            otel_endpoint=self.otel_endpoint,
            sample_rate=self.trace_sample_rate
        )

class TelemetryManager:
    """Manages OpenTelemetry setup and instrumentation"""
    
    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        
        # Custom metrics
        self.request_counter = None
        self.request_duration = None
        self.error_counter = None
        self.active_requests_gauge = None
        self.summarization_counter = None
        self.summarization_duration = None
        self.semantic_score_histogram = None
        
    def setup_telemetry(self) -> bool:
        """
        Initialize OpenTelemetry tracing and metrics.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Setup resource
            resource = Resource.create(self.config.resource_attributes)
            
            # Setup tracing
            self._setup_tracing(resource)
            
            # Setup metrics
            self._setup_metrics(resource)
            
            # Setup propagators
            self._setup_propagators()
            
            # Setup auto-instrumentation
            self._setup_auto_instrumentation()
            
            # Create custom metrics
            self._create_custom_metrics()
            
            logger.info("OpenTelemetry setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}", exc_info=True)
            return False
    
    def _setup_tracing(self, resource: Resource):
        """Setup distributed tracing"""
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Create OTLP span exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.config.otel_endpoint,
            insecure=True  # Use secure=False for gRPC without TLS
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        
        # Optional console exporter for debugging
        if self.config.enable_console_export:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            console_processor = BatchSpanProcessor(ConsoleSpanExporter())
            self.tracer_provider.add_span_processor(console_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(
            __name__,
            version=self.config.service_version
        )
        
        logger.info("Tracing setup completed", endpoint=self.config.otel_endpoint)
    
    def _setup_metrics(self, resource: Resource):
        """Setup metrics collection"""
        # Create OTLP metric exporter
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=self.config.otel_endpoint,
            insecure=True
        )
        
        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            exporter=otlp_metric_exporter,
            export_interval_millis=self.config.metrics_export_interval * 1000
        )
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Optional console metrics for debugging
        if self.config.enable_console_export:
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
            console_reader = PeriodicExportingMetricReader(
                exporter=ConsoleMetricExporter(),
                export_interval_millis=60000  # 1 minute for console
            )
            self.meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader, console_reader]
            )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(
            __name__,
            version=self.config.service_version
        )
        
        logger.info("Metrics setup completed")
    
    def _setup_propagators(self):
        """Setup trace context propagation"""
        # Use B3 propagation format (common in service mesh environments)
        set_global_textmap(B3MultiFormat())
        logger.info("B3 propagation format configured")
    
    def _setup_auto_instrumentation(self):
        """Setup automatic instrumentation for common libraries"""
        try:
            # Instrument HTTP clients
            HTTPXClientInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            
            logger.info("Auto-instrumentation setup completed")
            
        except Exception as e:
            logger.warning(f"Some auto-instrumentation failed: {e}")
    
    def _create_custom_metrics(self):
        """Create custom application metrics"""
        if not self.meter:
            logger.warning("Meter not available, skipping custom metrics creation")
            return
        
        # Request metrics
        self.request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        self.request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        self.error_counter = self.meter.create_counter(
            name="http_errors_total",
            description="Total number of HTTP errors",
            unit="1"
        )
        
        self.active_requests_gauge = self.meter.create_up_down_counter(
            name="http_active_requests",
            description="Number of active HTTP requests",
            unit="1"
        )
        
        # Summarization metrics
        self.summarization_counter = self.meter.create_counter(
            name="summarizations_total",
            description="Total number of summarization requests",
            unit="1"
        )
        
        self.summarization_duration = self.meter.create_histogram(
            name="summarization_duration_seconds",
            description="Time spent processing summarization requests",
            unit="s"
        )
        
        self.semantic_score_histogram = self.meter.create_histogram(
            name="semantic_similarity_score",
            description="Distribution of semantic similarity scores",
            unit="1"
        )
        
        logger.info("Custom metrics created successfully")
    
    def instrument_fastapi_app(self, app):
        """Instrument FastAPI application"""
        try:
            # Instrument FastAPI with custom configuration
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                meter_provider=self.meter_provider,
                excluded_urls="/healthz,/metrics",  # Exclude health/metrics endpoints
                server_request_hook=self._server_request_hook,
                client_request_hook=self._client_request_hook
            )
            
            logger.info("FastAPI instrumentation completed")
            
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)
    
    def _server_request_hook(self, span: trace.Span, scope: Dict[str, Any]):
        """Hook to add custom attributes to server spans"""
        if scope.get("type") == "http":
            # Add custom attributes
            headers = dict(scope.get("headers", []))
            tenant_id = headers.get(b"x-tenant-id")
            request_id = headers.get(b"x-request-id")
            
            if tenant_id:
                span.set_attribute("mcp.tenant_id", tenant_id.decode())
            if request_id:
                span.set_attribute("mcp.request_id", request_id.decode())
    
    def _client_request_hook(self, span: trace.Span, request):
        """Hook to add custom attributes to client spans"""
        # Add any custom client-side attributes
        span.set_attribute("mcp.client_type", "http")
    
    def record_request_metrics(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if self.request_counter and self.request_duration:
            attributes = {
                "method": method,
                "endpoint": endpoint,
                "status_code": str(status_code)
            }
            
            self.request_counter.add(1, attributes)
            self.request_duration.record(duration, attributes)
            
            # Record errors
            if status_code >= 400 and self.error_counter:
                error_attributes = {
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": str(status_code),
                    "error_type": "client_error" if status_code < 500 else "server_error"
                }
                self.error_counter.add(1, error_attributes)
    
    def record_active_requests(self, increment: bool = True):
        """Record active request count changes"""
        if self.active_requests_gauge:
            self.active_requests_gauge.add(1 if increment else -1)
    
    def record_summarization_metrics(self, model: str, status: str, duration: float, semantic_score: Optional[float] = None):
        """Record summarization-specific metrics"""
        attributes = {
            "model": model,
            "status": status
        }
        
        if self.summarization_counter:
            self.summarization_counter.add(1, attributes)
        
        if self.summarization_duration and duration > 0:
            self.summarization_duration.record(duration, {"model": model})
        
        if self.semantic_score_histogram and semantic_score is not None:
            self.semantic_score_histogram.record(semantic_score)
    
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> trace.Span:
        """Create a new span with optional attributes"""
        if not self.tracer:
            # Return a no-op span if tracer is not available
            return trace.NoOpSpan()
        
        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        return span
    
    def shutdown(self):
        """Shutdown telemetry providers"""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            
            logger.info("Telemetry shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}", exc_info=True)

# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None

def setup_telemetry() -> TelemetryManager:
    """
    Setup and return the global telemetry manager.
    
    Returns:
        TelemetryManager instance
    """
    global _telemetry_manager
    
    if _telemetry_manager is None:
        config = TelemetryConfig()
        _telemetry_manager = TelemetryManager(config)
        
        # Attempt to setup telemetry
        if not _telemetry_manager.setup_telemetry():
            logger.warning("Telemetry setup failed, continuing without telemetry")
    
    return _telemetry_manager

def get_telemetry_manager() -> Optional[TelemetryManager]:
    """Get the global telemetry manager if available"""
    return _telemetry_manager

def shutdown_telemetry():
    """Shutdown the global telemetry manager"""
    global _telemetry_manager
    
    if _telemetry_manager:
        _telemetry_manager.shutdown()
        _telemetry_manager = None
