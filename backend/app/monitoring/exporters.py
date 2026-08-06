"""Exporters for metrics and traces."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.monitoring.schemas import ExporterConfig, MetricPoint
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class Exporter(ABC):
    """Base exporter class."""

    @abstractmethod
    async def export(self, metrics: List) -> bool:
        """Export metrics."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown exporter."""
        pass


class PrometheusExporter:
    """Prometheus metrics exporter."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.port = self.config.get("port", 9090)
        self.path = self.config.get("path", "/metrics")
        self._server = None

    async def start(self):
        """Start Prometheus HTTP server."""
        try:
            from prometheus_client import start_http_server
            start_http_server(self.port)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus exporter: {e}")

    async def export(self, metrics) -> bool:
        """Export metrics to Prometheus (handled by HTTP server)."""
        return True

    async def shutdown(self):
        """Shutdown exporter."""
        pass


class OTLPExporter:
    """OpenTelemetry Protocol (OTLP) exporter for metrics and traces."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.endpoint = self.config.get("endpoint", "http://localhost:4317")
        self.headers = self.config.get("headers", {})
        self._exporter = None
        self._tracer_provider = None

    async def initialize(self):
        """Initialize OTLP exporter."""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            # Metrics exporter
            metric_exporter = OTLPMetricExporter(
                endpoint=self.endpoint,
                headers=self.headers,
            )
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=30000,
            )
            meter_provider = MeterProvider(metric_readers=[metric_reader])

            # Trace exporter
            span_exporter = OTLPSpanExporter(
                endpoint=self.endpoint,
                headers=self.headers,
            )
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

            self._meter_provider = meter_provider
            self._tracer_provider = tracer_provider

            logger.info(f"OTLP exporter initialized: {self.endpoint}")
        except ImportError:
            logger.warning("OpenTelemetry dependencies not installed, OTLP exporter disabled")
        except Exception as e:
            logger.error(f"Failed to initialize OTLP exporter: {e}")

    async def export(self, metrics) -> bool:
        """Export metrics (handled by periodic reader)."""
        return True

    async def shutdown(self):
        """Shutdown exporter."""
        if self._meter_provider:
            self._meter_provider.shutdown()
        if self._tracer_provider:
            self._tracer_provider.shutdown()


class JaegerExporter:
    """Jaeger trace exporter."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.endpoint = self.config.get("endpoint", "http://localhost:14268/api/traces")
        self._exporter = None

    async def initialize(self):
        """Initialize Jaeger exporter."""
        try:
            from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter as JaegerGrpcExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            self._exporter = JaegerGrpcExporter(
                endpoint=self.config.get("endpoint", "localhost:14250"),
            )

            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(BatchSpanProcessor(self._exporter))

            logger.info(f"Jaeger exporter initialized: {self.config.get('endpoint')}")
        except ImportError:
            logger.warning("Jaeger exporter dependencies not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Jaeger exporter: {e}")

    async def shutdown(self):
        if self._exporter:
            self._exporter.shutdown()


class ZipkinExporter:
    """Zipkin trace exporter."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.endpoint = self.config.get("endpoint", "http://localhost:9411/api/v2/spans")
        self._exporter = None

    async def initialize(self):
        try:
            from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter as ZipkinHttpExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            self._exporter = ZipkinHttpExporter(
                endpoint=self.endpoint,
            )

            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(BatchSpanProcessor(self._exporter))

            logger.info(f"Zipkin exporter initialized: {self.endpoint}")
        except ImportError:
            logger.warning("Zipkin exporter dependencies not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Zipkin exporter: {e}")

    async def shutdown(self):
        if self._exporter:
            self._exporter.shutdown()


class LoggingExporter:
    """Exporter that logs metrics to stdout (for debugging)."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.interval = self.config.get("interval_seconds", 60)

    async def export(self, metrics) -> bool:
        """Export metrics by logging them."""
        try:
            for metric in metrics:
                logger.info(
                    "Metric exported",
                    name=metric.name,
                    value=metric.value,
                    labels=metric.labels,
                    timestamp=metric.timestamp.isoformat(),
                )
            return True
        except Exception as e:
            logger.error(f"Logging exporter failed: {e}")
            return False

    async def shutdown(self):
        pass


class MultiExporter:
    """Exporter that forwards to multiple exporters."""

    def __init__(self, exporters: List = None):
        self.exporters = exporters or []

    def add_exporter(self, exporter):
        self.exporters.append(exporter)

    async def export(self, metrics) -> bool:
        """Export to all registered exporters."""
        results = []
        for exporter in self.exporters:
            try:
                result = await exporter.export(metrics)
                results.append(result)
            except Exception as e:
                logger.error(f"Exporter {type(exporter).__name__} failed: {e}")
                results.append(False)
        return all(results)

    async def shutdown(self):
        for exporter in self.exporters:
            try:
                await exporter.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down exporter {type(exporter).__name__}: {e}")


class ExporterManager:
    """Manages all exporters."""

    def __init__(self):
        self.exporters: Dict[str, Any] = {}
        self._multi_exporter = MultiExporter()

    async def initialize(self, config: Dict = None):
        """Initialize exporters based on configuration."""
        config = config or {}

        # Prometheus exporter (always enabled)
        prom_config = config.get("prometheus", {})
        if prom_config.get("enabled", True):
            prom_exporter = PrometheusExporter(prom_config)
            await prom_exporter.start()
            self.exporters["prometheus"] = prom_exporter
            self._multi_exporter.add_exporter(prom_exporter)

        # OTLP exporter
        otlp_config = config.get("otlp", {})
        if otlp_config.get("enabled", False):
            otlp_exporter = OTLPExporter(otlp_config)
            await otlp_exporter.initialize()
            self.exporters["otlp"] = otlp_exporter
            self._multi_exporter.add_exporter(otlp_exporter)

        # Jaeger exporter
        jaeger_config = config.get("jaeger", {})
        if jaeger_config.get("enabled", False):
            jaeger_exporter = JaegerExporter(jaeger_config)
            await jaeger_exporter.initialize()
            self.exporters["jaeger"] = jaeger_exporter
            self._multi_exporter.add_exporter(jaeger_exporter)

        # Zipkin exporter
        zipkin_config = config.get("zipkin", {})
        if zipkin_config.get("enabled", False):
            zipkin_exporter = ZipkinExporter(zipkin_config)
            await zipkin_exporter.initialize()
            self.exporters["zipkin"] = zipkin_exporter
            self._multi_exporter.add_exporter(zipkin_exporter)

        # Logging exporter (for debugging)
        logging_config = config.get("logging", {})
        if logging_config.get("enabled", False):
            logging_exporter = LoggingExporter(logging_config)
            self.exporters["logging"] = logging_exporter
            self._multi_exporter.add_exporter(logging_exporter)

        logger.info(f"Initialized {len(self.exporters)} exporters")

    async def export_metrics(self, metrics) -> bool:
        """Export metrics to all exporters."""
        return await self._multi_exporter.export(metrics)

    async def shutdown(self):
        """Shutdown all exporters."""
        await self._multi_exporter.shutdown()
        self.exporters.clear()


# Global exporter manager
_exporter_manager: Optional["ExporterManager"] = None


async def get_exporter_manager(config: Dict = None) -> "ExporterManager":
    """Get or create the global exporter manager."""
    global _exporter_manager
    if _exporter_manager is None:
        _exporter_manager = ExporterManager()
        await _exporter_manager.initialize(config)
    return _exporter_manager