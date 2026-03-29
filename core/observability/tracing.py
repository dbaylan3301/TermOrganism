from __future__ import annotations

import os
from typing import Any

_OTE = None
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _OTE = True
except Exception:
    trace = None
    TracerProvider = None
    BatchSpanProcessor = None
    OTLPSpanExporter = None
    _OTE = False


class NoopRepairTracer:
    enabled = False

    def emit(self, operation: str, payload: dict[str, Any], file_path: str | None, fast: bool):
        return None


class RepairTracer(NoopRepairTracer):
    enabled = True
    _initialized = False
    _tracer = None

    def __init__(self, service_name: str = "termorganism"):
        if not _OTE:
            raise RuntimeError("OpenTelemetry not available")

        if not self.__class__._initialized:
            provider = TracerProvider()
            exporter = OTLPSpanExporter(
                endpoint=os.getenv("TERMORGANISM_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
            )
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            self.__class__._tracer = trace.get_tracer(service_name)
            self.__class__._initialized = True

        self.tracer = self.__class__._tracer

    def emit(self, operation: str, payload: dict[str, Any], file_path: str | None, fast: bool):
        metrics = payload.get("metrics") or {}
        result = payload.get("result") or {}
        confidence = payload.get("confidence") or {}

        with self.tracer.start_as_current_span(operation) as span:
            span.set_attribute("termorganism.fast", bool(fast))
            span.set_attribute("termorganism.file_path", str(file_path or ""))
            span.set_attribute("termorganism.mode", str(metrics.get("mode") or ("fast" if fast else "normal")))
            span.set_attribute("termorganism.total_ms", float(metrics.get("total_ms", 0.0) or 0.0))
            span.set_attribute("termorganism.semantic_ms", float(metrics.get("semantic_ms", 0.0) or 0.0))
            span.set_attribute("termorganism.planning_ms", float(metrics.get("planning_ms", 0.0) or 0.0))
            span.set_attribute("termorganism.selection_ms", float(metrics.get("selection_ms", 0.0) or 0.0))
            span.set_attribute("termorganism.routes", ",".join(payload.get("routes") or []))
            span.set_attribute("termorganism.result_kind", str(result.get("kind") or ""))
            span.set_attribute(
                "termorganism.result_confidence",
                float((confidence.get("score")) or result.get("confidence") or 0.0),
            )
            span.set_attribute("termorganism.verify_ok", bool((payload.get("verify") or {}).get("ok")))

            verification = payload.get("verification") or {}
            jsv = verification.get("javascript") if isinstance(verification, dict) else None
            if isinstance(jsv, dict):
                span.set_attribute("termorganism.javascript_verify_ok", bool(jsv.get("ok")))
                span.set_attribute("termorganism.javascript_verify_confidence", float(jsv.get("confidence", 0.0) or 0.0))

            memory = payload.get("memory") or {}
            if isinstance(memory, dict):
                span.set_attribute("termorganism.memory_prior", float(memory.get("memory_prior", 0.0) or 0.0))
                span.set_attribute("termorganism.similar_repairs_found", int(memory.get("similar_repairs_found", 0) or 0))


_TRACER_SINGLETON = None


def get_repair_tracer() -> NoopRepairTracer | RepairTracer:
    global _TRACER_SINGLETON
    if _TRACER_SINGLETON is not None:
        return _TRACER_SINGLETON

    enabled = os.getenv("TERMORGANISM_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled or not _OTE:
        _TRACER_SINGLETON = NoopRepairTracer()
        return _TRACER_SINGLETON

    try:
        _TRACER_SINGLETON = RepairTracer(service_name=os.getenv("TERMORGANISM_SERVICE_NAME", "termorganism"))
    except Exception:
        _TRACER_SINGLETON = NoopRepairTracer()
    return _TRACER_SINGLETON


def emit_repair_trace(operation: str, payload: dict[str, Any], file_path: str | None, fast: bool):
    tracer = get_repair_tracer()
    return tracer.emit(operation, payload, file_path, fast)
