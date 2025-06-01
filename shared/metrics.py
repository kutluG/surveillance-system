"""
Prometheus metrics setup and FastAPI instrumentation for all services.
"""
from typing import Callable
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from fastapi import FastAPI, Request, Response

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["service", "method", "endpoint", "http_status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Histogram of HTTP request latency in seconds",
    ["service", "method", "endpoint"],
)

def instrument_app(app: FastAPI, service_name: str) -> None:
    """
    Add Prometheus instrumentation middleware and /metrics endpoint to a FastAPI app.
    :param app: FastAPI instance to instrument.
    :param service_name: Name of the service for labeling metrics.
    """
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - start_time

        # Label values
        method = request.method
        # Use path template if available, else raw path
        endpoint = request.scope.get("route").path if request.scope.get("route") else request.url.path
        status_code = str(response.status_code)

        # Update metrics
        REQUEST_COUNT.labels(
            service=service_name,
            method=method,
            endpoint=endpoint,
            http_status=status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            service=service_name,
            method=method,
            endpoint=endpoint,
        ).observe(elapsed)

        return response

    @app.get("/metrics")
    async def metrics() -> Response:
        """
        Expose Prometheus metrics.
        """
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)