from __future__ import annotations

"""Prometheus metrics for the Feishu Codex Stack Control Center."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# ---------------------------------------------------------------------------
# Existing metrics (acc_ prefix, kept for backward compatibility)
# ---------------------------------------------------------------------------

_API_REQUEST_COUNT = Counter(
    "acc_api_requests_total",
    "Total API requests served.",
    ["endpoint", "method", "status_code"],
    registry=REGISTRY,
)

_API_REQUEST_LATENCY = Histogram(
    "acc_api_request_duration_seconds",
    "API request latency in seconds.",
    ["endpoint", "method"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

_COMPONENT_STATUS = Gauge(
    "acc_component_status",
    "Component running status (1=running, 0=stopped).",
    ["component"],
    registry=REGISTRY,
)

_OPERATION_COUNT = Counter(
    "acc_operations_total",
    "Total control operations executed.",
    ["component", "action", "outcome"],
    registry=REGISTRY,
)

_WS_CONNECTIONS = Gauge(
    "acc_websocket_connections",
    "Current open WebSocket connections.",
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Phase-7 metrics (standard naming, as specified in requirements)
# ---------------------------------------------------------------------------

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests processed.",
    ["method", "status"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

agent_status = Gauge(
    "agent_status",
    "Agent online status (1=online, 0=offline).",
    ["agent"],
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def record_api_request(endpoint: str, method: str, status_code: int, duration: float) -> None:
    _API_REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=str(status_code)).inc()
    _API_REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)
    http_requests_total.labels(method=method, status=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_operation(component: str, action: str, ok: bool) -> None:
    _OPERATION_COUNT.labels(
        component=component, action=action, outcome="success" if ok else "failure"
    ).inc()


def set_component_status(component: str, running: bool) -> None:
    _COMPONENT_STATUS.labels(component=component).set(1.0 if running else 0.0)


def set_ws_connections(count: int) -> None:
    _WS_CONNECTIONS.set(float(count))


def set_agent_status(agent: str, online: bool) -> None:
    """Set the agent_status gauge for a named agent."""
    agent_status.labels(agent=agent).set(1.0 if online else 0.0)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)


__all__ = [
    "record_api_request",
    "record_operation",
    "set_component_status",
    "set_ws_connections",
    "set_agent_status",
    "render_metrics",
]
