from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.autofix import run_autofix, finalize_repair_payload
from core.orchestrator_fallback import FallbackOrchestrator
from core.orchestrator_hot_force import HotCacheForcePath
from core.repro.harness import run_python_file


@dataclass
class RepairRequest:
    file_path: str
    context: dict[str, Any]
    mode: str = "auto"


class TermOrganismDaemon:
    """
    Persistent daemon:
    - hot_force direct path
    - fallback chain for auto/fast/normal
    """

    def __init__(self, socket_path: Path = Path("/tmp/termorganism.sock")):
        self.socket_path = socket_path
        self.hot_force = HotCacheForcePath()
        self.fallback = FallbackOrchestrator(
            run_hot_force=self._run_hot_force,
            run_existing_pipeline=self._run_existing_pipeline,
            should_hot_force=self._should_hot_force,
        )
        self._prewarm()

    def _prewarm(self):
        import ast
        import pathlib
        _ = ast, pathlib
        _ = self.hot_force.HOT_REPAIRS
        print("Daemon warmed up and ready", file=sys.stderr)

    def _sync_hot_cache_confidence(self, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            return result

        memory = result.get("memory") or {}
        hot = memory.get("hot_cache") if isinstance(memory, dict) else None
        if not isinstance(hot, dict):
            return result

        conf = result.get("confidence") or {}
        if not isinstance(conf, dict):
            conf = {}
            result["confidence"] = conf

        verify_ok = bool((result.get("verify") or {}).get("ok"))
        branch_ok = bool(((result.get("branch_result") or {}).get("ok")))
        behavioral_ok = bool(((result.get("behavioral_verify") or {}).get("ok")))
        contract_ok = bool(((result.get("contract_result") or {}).get("ok")))
        success = verify_ok or branch_ok or behavioral_ok or contract_ok
        if not success:
            return result

        result_obj = result.get("result") or {}
        best_plan = result.get("best_plan") or {}

        base_score = float(
            conf.get("score", 0.0)
            or (result_obj.get("confidence") if isinstance(result_obj, dict) else 0.0)
            or (best_plan.get("confidence") if isinstance(best_plan, dict) else 0.0)
            or 0.0
        )

        hot_score = float(hot.get("confidence", base_score) or base_score)
        boosted = max(base_score, hot_score)

        conf["score"] = boosted
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = boosted - base_score

        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

        return result

    def _build_context(self, file_path: Path) -> dict[str, Any]:
        repro = run_python_file(str(file_path))
        stderr = str(getattr(repro, "stderr", "") or "")
        return {
            "error_text": stderr,
            "traceback": [],
            "repro": repro.to_dict() if hasattr(repro, "to_dict") else {},
        }

    def _should_hot_force(self, context: dict[str, Any]) -> bool:
        explicit = str(context.get("signature") or "").strip().lower()
        if explicit in {"filenotfounderror:open:runtime", "importerror:no_module_named"}:
            return True

        text = str(context.get("error_text") or "").lower()
        if "filenotfounderror" in text and ("open(" in text or "read_text" in text or "no such file or directory" in text):
            return True
        if "modulenotfounderror" in text or "no module named" in text or "importerror" in text:
            return True
        return False

    async def _run_hot_force(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self.hot_force.repair, file_path, context)

    def _run_existing_pipeline_sync(self, file_path: Path, mode: str, context: dict[str, Any]) -> dict[str, Any]:
        repro = run_python_file(str(file_path))
        error_text = str(getattr(repro, "stderr", "") or "")
        result = run_autofix(
            error_text=error_text,
            file_path=str(file_path),
            fast=(mode == "fast"),
        )
        result = finalize_repair_payload(result, fast=(mode == "fast"))
        result = self._sync_hot_cache_confidence(result)
        return result

    async def _run_existing_pipeline(self, file_path: Path, mode: str, context: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._run_existing_pipeline_sync,
            file_path,
            mode,
            context,
        )

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        start = time.monotonic()

        try:
            data = await reader.read(65536)
            request = json.loads(data.decode("utf-8"))

            raw_file = request.get("file_path") or request.get("file")
            if not raw_file:
                raise ValueError("missing file_path/file")
            file_path = Path(raw_file)

            context = request.get("context") or {}
            mode = str(request.get("mode") or "auto")

            if not file_path.exists():
                result = {
                    "success": False,
                    "mode": "daemon",
                    "error": f"target does not exist: {file_path}",
                }
            else:
                if request.get("fast_path") == "hot_force":
                    hot_ctx = {
                        "error_text": "Hot force signature request",
                        "traceback": [{"error_type": "HotForceSignature", "function": "hot_force"}],
                        "signature": request.get("signature"),
                    }
                    result = await self._run_hot_force(file_path, hot_ctx)
                    result["fallback_chain"] = ["hot_force"]
                else:
                    if not context:
                        context = self._build_context(file_path)
                    result = await self.fallback.repair(file_path, context, mode=mode)

        except Exception as exc:
            result = {
                "success": False,
                "mode": "daemon",
                "error": f"{type(exc).__name__}: {exc}",
            }

        elapsed = (time.monotonic() - start) * 1000.0
        if isinstance(result, dict):
            result.setdefault("daemon", {})
            result["daemon"]["socket"] = str(self.socket_path)
            result["daemon"]["request_ms"] = round(elapsed, 3)

        writer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        print(f"Request handled in {elapsed:.2f}ms", file=sys.stderr)

    async def start(self):
        if self.socket_path.exists():
            self.socket_path.unlink()

        server = await asyncio.start_unix_server(
            self.handle_request,
            str(self.socket_path),
        )

        print(f"Daemon listening on {self.socket_path}", file=sys.stderr)

        async with server:
            await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", default="/tmp/termorganism.sock")
    args = parser.parse_args()

    daemon = TermOrganismDaemon(socket_path=Path(args.socket))
    asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
