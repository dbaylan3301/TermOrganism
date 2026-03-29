from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

_PROM = None
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    _PROM = True
except Exception:
    Counter = Histogram = Gauge = start_http_server = None
    _PROM = False


class NoopRepairMetrics:
    enabled = False

    @contextmanager
    def track_active(self):
        yield

    def record_repair(self, mode: str, language: str, duration: float, success: bool, confidence: float):
        return None

    def record_cache_hit(self, cache_type: str):
        return None

    def set_memory_size(self, project: str, value: int):
        return None

    def set_sandbox_pool_size(self, value: int):
        return None


class RepairMetrics(NoopRepairMetrics):
    enabled = True
    _server_started_ports: set[int] = set()

    def __init__(self, port: int = 9108):
        if not _PROM:
            raise RuntimeError("prometheus_client not available")

        self.repairs_total = Counter(
            "termorganism_repairs_total",
            "Total repairs attempted",
            ["mode", "status", "language"],
        )
        self.cache_hits = Counter(
            "termorganism_cache_hits_total",
            "Cache hits",
            ["cache_type"],
        )
        self.repair_duration = Histogram(
            "termorganism_repair_duration_seconds",
            "Repair latency",
            ["mode", "language"],
            buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 25.0, 60.0],
        )
        self.confidence_distribution = Histogram(
            "termorganism_confidence",
            "Repair confidence scores",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )
        self.active_repairs = Gauge(
            "termorganism_active_repairs",
            "Currently running repairs",
        )
        self.memory_size = Gauge(
            "termorganism_memory_records",
            "Total memory records",
            ["project"],
        )
        self.sandbox_pool_size = Gauge(
            "termorganism_sandbox_pool_available",
            "Available sandboxes",
        )

        if port not in self._server_started_ports:
            start_http_server(port)
            self._server_started_ports.add(port)

    @contextmanager
    def track_active(self):
        self.active_repairs.inc()
        try:
            yield
        finally:
            self.active_repairs.dec()

    def record_repair(self, mode: str, language: str, duration: float, success: bool, confidence: float):
        status = "success" if success else "failure"
        self.repairs_total.labels(mode=mode, status=status, language=language).inc()
        self.repair_duration.labels(mode=mode, language=language).observe(max(0.0, float(duration)))
        self.confidence_distribution.observe(max(0.0, min(1.0, float(confidence))))

    def record_cache_hit(self, cache_type: str):
        self.cache_hits.labels(cache_type=cache_type).inc()

    def set_memory_size(self, project: str, value: int):
        self.memory_size.labels(project=project).set(int(value))

    def set_sandbox_pool_size(self, value: int):
        self.sandbox_pool_size.set(int(value))


_METRICS_SINGLETON: Any = None


def get_repair_metrics() -> NoopRepairMetrics | RepairMetrics:
    global _METRICS_SINGLETON
    if _METRICS_SINGLETON is not None:
        return _METRICS_SINGLETON

    enabled = os.getenv("TERMORGANISM_METRICS", "").strip().lower() in {"1", "true", "yes", "on"}
    port = int(os.getenv("TERMORGANISM_METRICS_PORT", "9108"))

    if not enabled or not _PROM:
        _METRICS_SINGLETON = NoopRepairMetrics()
        return _METRICS_SINGLETON

    try:
        _METRICS_SINGLETON = RepairMetrics(port=port)
    except Exception:
        _METRICS_SINGLETON = NoopRepairMetrics()
    return _METRICS_SINGLETON
