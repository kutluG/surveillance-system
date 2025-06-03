import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, OTLPSpanExporter

def configure_tracing(service_name: str) -> None:
    """
    Configure OpenTelemetry tracing. If OTEL_EXPORTER_OTLP_ENDPOINT is set,
    exports to OTLP; otherwise logs spans to console.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    else:
        exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)
