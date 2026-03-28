from __future__ import annotations

import os
from typing import Any

from core.verify.microvm import (
    SandboxConfig,
    execute_python_in_sandbox_sync,
    sandbox_result_to_dict,
)


def build_sandbox_config(
    *,
    backend: str | None = None,
    timeout_sec: int | None = None,
    memory_mb: int | None = None,
    cpu_count: int | None = None,
) -> SandboxConfig:
    return SandboxConfig(
        backend=backend or os.getenv("TERMORGANISM_SANDBOX_BACKEND", "local"),
        timeout_sec=int(timeout_sec or os.getenv("TERMORGANISM_SANDBOX_TIMEOUT", "5")),
        memory_mb=int(memory_mb or os.getenv("TERMORGANISM_SANDBOX_MEMORY_MB", "256")),
        cpu_count=int(cpu_count or os.getenv("TERMORGANISM_SANDBOX_CPU_COUNT", "1")),
        network_enabled=False,
    )


def run_isolated_python_code(
    code: str,
    *,
    backend: str | None = None,
    timeout_sec: int | None = None,
    memory_mb: int | None = None,
    cpu_count: int | None = None,
) -> dict[str, Any]:
    cfg = build_sandbox_config(
        backend=backend,
        timeout_sec=timeout_sec,
        memory_mb=memory_mb,
        cpu_count=cpu_count,
    )
    return sandbox_result_to_dict(execute_python_in_sandbox_sync(code, cfg))
