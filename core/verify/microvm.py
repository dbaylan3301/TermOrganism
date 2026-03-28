from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class SandboxConfig:
    backend: str = "local"               # local | gvisor | firecracker
    timeout_sec: int = 5
    memory_mb: int = 256
    cpu_count: int = 1
    network_enabled: bool = False


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    resource_usage: dict[str, Any]
    backend: str
    fallback_used: bool = False


class BaseSandbox:
    backend_name = "base"

    def is_available(self) -> bool:
        return False

    async def execute_python(self, code: str, config: SandboxConfig) -> SandboxResult:
        raise NotImplementedError


class LocalSandbox(BaseSandbox):
    backend_name = "local"

    def is_available(self) -> bool:
        return True

    async def execute_python(self, code: str, config: SandboxConfig) -> SandboxResult:
        start = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="termorganism_local_sb_") as td:
            script = Path(td) / "script.py"
            script.write_text(code, encoding="utf-8")

            proc = await asyncio.create_subprocess_exec(
                "python3",
                str(script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=config.timeout_sec)
                return SandboxResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode(errors="replace"),
                    stderr=stderr.decode(errors="replace"),
                    exit_code=int(proc.returncode or 0),
                    duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                    resource_usage={
                        "memory_mb_limit": config.memory_mb,
                        "cpu_count": config.cpu_count,
                    },
                    backend=self.backend_name,
                    fallback_used=False,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr="Timeout",
                    exit_code=124,
                    duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                    resource_usage={
                        "memory_mb_limit": config.memory_mb,
                        "cpu_count": config.cpu_count,
                    },
                    backend=self.backend_name,
                    fallback_used=False,
                )


class GVisorSandbox(BaseSandbox):
    backend_name = "gvisor"

    def __init__(self, runsc_bin: str | None = None):
        self.runsc_bin = runsc_bin or os.getenv("TERMORGANISM_RUNSC_BIN", "/usr/local/bin/runsc")

    def is_available(self) -> bool:
        return shutil.which(self.runsc_bin) is not None or Path(self.runsc_bin).exists()

    async def execute_python(self, code: str, config: SandboxConfig) -> SandboxResult:
        start = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="termorganism_gvisor_") as td:
            bundle = Path(td)
            rootfs = bundle / "rootfs"
            rootfs.mkdir(parents=True, exist_ok=True)

            # Minimal bundle: mount script into rootfs and invoke host python path expectation inside sandbox.
            script = rootfs / "script.py"
            script.write_text(code, encoding="utf-8")

            cfg = {
                "ociVersion": "1.0.2",
                "process": {
                    "terminal": False,
                    "args": ["python3", "/script.py"],
                    "env": ["PYTHONUNBUFFERED=1"],
                    "cwd": "/",
                },
                "root": {
                    "path": "rootfs",
                    "readonly": False,
                },
                "hostname": "termorganism-sandbox",
                "linux": {
                    "namespaces": [
                        {"type": "pid"},
                        {"type": "ipc"},
                        {"type": "uts"},
                        {"type": "mount"},
                        {"type": "network"},
                    ],
                    "resources": {
                        "memory": {"limit": int(config.memory_mb) * 1024 * 1024},
                        "cpu": {"shares": 1024},
                    },
                },
            }
            (bundle / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

            sandbox_id = f"termorganism-{uuid.uuid4().hex[:8]}"
            proc = await asyncio.create_subprocess_exec(
                self.runsc_bin,
                "run",
                "-bundle",
                str(bundle),
                sandbox_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=config.timeout_sec)
                return SandboxResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode(errors="replace"),
                    stderr=stderr.decode(errors="replace"),
                    exit_code=int(proc.returncode or 0),
                    duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                    resource_usage={
                        "memory_mb_limit": config.memory_mb,
                        "cpu_count": config.cpu_count,
                    },
                    backend=self.backend_name,
                    fallback_used=False,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr="Timeout",
                    exit_code=124,
                    duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                    resource_usage={
                        "memory_mb_limit": config.memory_mb,
                        "cpu_count": config.cpu_count,
                    },
                    backend=self.backend_name,
                    fallback_used=False,
                )


class FirecrackerSandbox(BaseSandbox):
    backend_name = "firecracker"

    def __init__(
        self,
        firecracker_bin: str | None = None,
        helper_bin: str | None = None,
    ):
        self.firecracker_bin = firecracker_bin or os.getenv("TERMORGANISM_FIRECRACKER_BIN", "/usr/local/bin/firecracker")
        self.helper_bin = helper_bin or os.getenv("TERMORGANISM_FIRECRACKER_HELPER", "./scripts/termorganism-firecracker-run")

    def is_available(self) -> bool:
        # We require both firecracker and helper wrapper to exist.
        fc_ok = shutil.which(self.firecracker_bin) is not None or Path(self.firecracker_bin).exists()
        helper_ok = shutil.which(self.helper_bin) is not None or Path(self.helper_bin).exists()
        return fc_ok and helper_ok

    async def execute_python(self, code: str, config: SandboxConfig) -> SandboxResult:
        start = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            self.helper_bin,
            "--timeout-sec", str(config.timeout_sec),
            "--memory-mb", str(config.memory_mb),
            "--cpu-count", str(config.cpu_count),
            "--backend", "firecracker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(code.encode("utf-8")), timeout=config.timeout_sec + 2)
            parsed = None
            try:
                parsed = json.loads(stdout.decode(errors="replace"))
            except Exception:
                parsed = None

            if isinstance(parsed, dict):
                return SandboxResult(
                    success=bool(parsed.get("exit_code", 1) == 0),
                    stdout=str(parsed.get("stdout", "")),
                    stderr=str(parsed.get("stderr", "")),
                    exit_code=int(parsed.get("exit_code", 1)),
                    duration_ms=float(parsed.get("duration_ms", round((time.perf_counter() - start) * 1000.0, 3))),
                    resource_usage=dict(parsed.get("resource_usage", {})),
                    backend=self.backend_name,
                    fallback_used=False,
                )

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                exit_code=int(proc.returncode or 0),
                duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                resource_usage={
                    "memory_mb_limit": config.memory_mb,
                    "cpu_count": config.cpu_count,
                },
                backend=self.backend_name,
                fallback_used=False,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Timeout",
                exit_code=124,
                duration_ms=round((time.perf_counter() - start) * 1000.0, 3),
                resource_usage={
                    "memory_mb_limit": config.memory_mb,
                    "cpu_count": config.cpu_count,
                },
                backend=self.backend_name,
                fallback_used=False,
            )


def select_backend(config: SandboxConfig):
    requested = (config.backend or "local").lower().strip()
    candidates = []
    if requested == "firecracker":
        candidates = [FirecrackerSandbox(), GVisorSandbox(), LocalSandbox()]
    elif requested == "gvisor":
        candidates = [GVisorSandbox(), LocalSandbox()]
    else:
        candidates = [LocalSandbox()]

    for backend in candidates:
        if backend.is_available():
            return backend
    return LocalSandbox()


async def execute_python_in_sandbox(code: str, config: SandboxConfig | None = None) -> SandboxResult:
    config = config or SandboxConfig()
    selected = select_backend(config)
    result = await selected.execute_python(code, config)
    if selected.backend_name != (config.backend or "local"):
        result.fallback_used = True
    return result


def execute_python_in_sandbox_sync(code: str, config: SandboxConfig | None = None) -> SandboxResult:
    return asyncio.run(execute_python_in_sandbox(code, config))


def sandbox_result_to_dict(result: SandboxResult) -> dict[str, Any]:
    return asdict(result)
