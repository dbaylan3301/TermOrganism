from __future__ import annotations

import asyncio
import ast
import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.experts.dependency import DependencyExpert
from core.experts.file_runtime import FileRuntimeExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.python_syntax import PythonSyntaxExpert
from core.repro.harness import run_python_file


@dataclass
class VerificationResult:
    ok: bool
    confidence: float
    runtime: dict[str, Any]
    static_verify: dict[str, Any]
    typecheck_ok: bool = False


@dataclass
class FastRepairResult:
    success: bool
    repair_applied: bool
    latency_ms: float
    confidence: float
    method: str              # cache_hit | parallel | fallback
    trace: list[str]
    candidate: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    cache_key: str | None = None


class ExpertPool:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.experts = [
            ("syntax", PythonSyntaxExpert()),
            ("dependency", DependencyExpert()),
            ("runtime", FileRuntimeExpert()),
            ("memory", MemoryRetrievalExpert()),
            ("llm", LLMFallbackExpert()),
        ]

    async def generate_parallel(
        self,
        *,
        error_text: str,
        file_path: str,
        max_candidates: int = 3,
        timeout: float = 1.0,
    ) -> list[dict[str, Any]]:
        async def _run_one(name: str, expert) -> list[dict[str, Any]]:
            def _call():
                return expert.propose(error_text=error_text, file_path=file_path)
            try:
                raw = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout)
            except Exception:
                return []
            out: list[dict[str, Any]] = []
            if isinstance(raw, dict):
                raw.setdefault("expert", name)
                out.append(raw)
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        item.setdefault("expert", name)
                        out.append(item)
            return out

        tasks = [_run_one(name, expert) for name, expert in self.experts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            candidates.extend(r[:2])

        # keep only source-bearing candidates when possible
        with_code = [c for c in candidates if str(c.get("candidate_code") or "").strip()]
        base = with_code if with_code else candidates
        base.sort(
            key=lambda c: (
                -float(c.get("confidence", 0.0) or 0.0),
                str(c.get("expert") or ""),
                str(c.get("summary") or ""),
            )
        )
        return base[:max_candidates]


class FastRepairMode:
    """
    Experimental fast repair engine.
    Goal: sub-3s path for safe single-file dependency/syntax cases.
    """

    _embedder = None

    def __init__(self, cache_dir: Path = Path(".termorganism/cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ast_dir = self.cache_dir / "ast"
        self.result_dir = self.cache_dir / "results"
        self.ast_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.expert_pool = ExpertPool(max_workers=4)

    async def repair(self, target_file: Path, failure_context: dict[str, Any]) -> FastRepairResult:
        loop = asyncio.get_running_loop()
        start = loop.time()
        trace: list[str] = []

        cache_key = self._compute_cache_key(target_file, failure_context)
        trace.append("cache_lookup")
        cached = await self._check_cache(cache_key)
        if isinstance(cached, dict):
            candidate = cached.get("candidate") or {}
            verification = cached.get("verification") or {}
            confidence = float(cached.get("confidence", 0.0) or 0.0)
            if candidate and confidence >= 0.90:
                elapsed = (loop.time() - start) * 1000.0
                trace.extend(["cache_hit", "apply_cached"])
                return FastRepairResult(
                    success=True,
                    repair_applied=True,
                    latency_ms=elapsed,
                    confidence=confidence,
                    method="cache_hit",
                    trace=trace,
                    candidate=candidate,
                    verification=verification,
                    cache_key=cache_key,
                )

        trace.append("ast_localize_parallel")
        ast_task = asyncio.create_task(self._fast_ast_parse(target_file))
        localize_task = asyncio.create_task(self._fast_localize(target_file, failure_context))
        ast_result, fault_location = await asyncio.gather(ast_task, localize_task)

        trace.append("expert_gen")
        candidates = await self.expert_pool.generate_parallel(
            error_text=str(failure_context.get("error_text") or ""),
            file_path=str(target_file),
            max_candidates=3,
            timeout=1.0,
        )

        trace.append("rank")
        best_candidate = await self._fast_rank(candidates, ast_result, str(failure_context.get("error_text") or ""))

        if not best_candidate:
            elapsed = (loop.time() - start) * 1000.0
            return FastRepairResult(
                success=False,
                repair_applied=False,
                latency_ms=elapsed,
                confidence=0.0,
                method="fallback",
                trace=trace + ["no_candidate"],
                candidate=None,
                verification=None,
                cache_key=cache_key,
            )

        trace.append("verify")
        verified = await self._fast_verify(best_candidate, target_file)

        elapsed = (loop.time() - start) * 1000.0

        if verified.ok:
            trace.append("cache_write")
            await self._write_cache(cache_key, {
                "candidate": best_candidate,
                "verification": {
                    "ok": verified.ok,
                    "confidence": verified.confidence,
                    "runtime": verified.runtime,
                    "static_verify": verified.static_verify,
                    "typecheck_ok": verified.typecheck_ok,
                },
                "confidence": verified.confidence,
            })

        return FastRepairResult(
            success=verified.ok,
            repair_applied=verified.ok,
            latency_ms=elapsed,
            confidence=verified.confidence,
            method="parallel",
            trace=trace,
            candidate=best_candidate,
            verification={
                "ok": verified.ok,
                "confidence": verified.confidence,
                "runtime": verified.runtime,
                "static_verify": verified.static_verify,
                "typecheck_ok": verified.typecheck_ok,
            },
            cache_key=cache_key,
        )

    def _compute_cache_key(self, file: Path, context: dict[str, Any]) -> str:
        try:
            content = file.read_text(encoding="utf-8")
        except Exception:
            content = ""
        context_str = json.dumps(context, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(f"{content}\n{context_str}".encode("utf-8")).hexdigest()[:16]

    async def _check_cache(self, cache_key: str) -> dict[str, Any] | None:
        p = self.result_dir / f"{cache_key}.json"
        if not p.exists():
            return None
        try:
            return json.loads(await asyncio.to_thread(p.read_text, encoding="utf-8"))
        except Exception:
            return None

    async def _write_cache(self, cache_key: str, payload: dict[str, Any]) -> None:
        p = self.result_dir / f"{cache_key}.json"
        await asyncio.to_thread(
            p.write_text,
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _fast_ast_parse(self, file: Path) -> dict[str, Any]:
        file_hash = hashlib.sha256(file.read_bytes()).hexdigest()[:12]
        cache_file = self.ast_dir / f"{file_hash}.ast.json"
        if cache_file.exists():
            try:
                return json.loads(await asyncio.to_thread(cache_file.read_text, encoding="utf-8"))
            except Exception:
                pass

        data: dict[str, Any]
        try:
            # optional tree-sitter path
            from tree_sitter import Language, Parser
            import tree_sitter_python as tspython

            py_lang = Language(tspython.language())
            parser = Parser(py_lang)
            root = parser.parse(file.read_bytes()).root_node
            data = {
                "backend": "tree_sitter",
                "type": root.type,
                "child_count": root.child_count,
                "fault_relevant_nodes": self._extract_fault_relevant_nodes_ts(root),
            }
        except Exception:
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
                data = {
                    "backend": "ast",
                    "fault_relevant_nodes": self._extract_fault_relevant_nodes_ast(tree),
                }
            except Exception as exc:
                data = {"backend": "ast", "error": str(exc), "fault_relevant_nodes": []}

        await asyncio.to_thread(
            cache_file.write_text,
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return data

    def _extract_fault_relevant_nodes_ast(self, tree: ast.AST) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call, ast.Assign, ast.FunctionDef, ast.ClassDef)):
                out.append({
                    "type": type(node).__name__,
                    "line": getattr(node, "lineno", None),
                })
                if len(out) >= 32:
                    break
        return out

    def _extract_fault_relevant_nodes_ts(self, root) -> list[dict[str, Any]]:
        out = []
        stack = [root]
        while stack and len(out) < 32:
            node = stack.pop()
            out.append({
                "type": getattr(node, "type", None),
                "start": getattr(node, "start_point", None),
                "end": getattr(node, "end_point", None),
            })
            try:
                children = list(node.children)
            except Exception:
                children = []
            stack.extend(reversed(children))
        return out

    async def _fast_localize(self, target_file: Path, context: dict[str, Any]) -> str:
        tb = context.get("traceback") or []
        if tb:
            last = tb[-1]
            return f"{last.get('filename')}:{last.get('lineno')}"
        return str(target_file)

    async def _fast_rank(
        self,
        candidates: list[dict[str, Any]],
        ast_context: dict[str, Any],
        error_text: str,
    ) -> dict[str, Any] | None:
        if not candidates:
            return None

        # Optional embedding model path; singleton to avoid reload cost.
        try:
            if FastRepairMode._embedder is None:
                from sentence_transformers import SentenceTransformer
                FastRepairMode._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            model = FastRepairMode._embedder
            ast_embedding = await asyncio.to_thread(model.encode, json.dumps(ast_context, ensure_ascii=False))
            scored = []
            for cand in candidates:
                desc = str(cand.get("summary") or cand.get("description") or cand.get("semantic_claim") or "")
                cand_embedding = await asyncio.to_thread(model.encode, desc)
                sim = float((ast_embedding @ cand_embedding))
                score = sim + float(cand.get("confidence", 0.0) or 0.0)
                scored.append((score, cand))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]
        except Exception:
            # cheap lexical fallback
            err_tokens = set(re.findall(r"[A-Za-z_]+", error_text.lower()))
            ast_tokens = set(re.findall(r"[A-Za-z_]+", json.dumps(ast_context).lower()))
            scored = []
            for cand in candidates:
                desc = str(cand.get("summary") or cand.get("description") or cand.get("semantic_claim") or "").lower()
                toks = set(re.findall(r"[A-Za-z_]+", desc))
                overlap = len(toks & (err_tokens | ast_tokens))
                score = overlap + float(cand.get("confidence", 0.0) or 0.0)
                scored.append((score, cand))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]

    async def _fast_verify(self, candidate: dict[str, Any], original: Path) -> VerificationResult:
        code = str(candidate.get("candidate_code") or candidate.get("code") or "")
        if not code.strip():
            return VerificationResult(
                ok=False,
                confidence=0.0,
                runtime={"ok": False, "returncode": 1, "stdout": "", "stderr": "empty candidate code"},
                static_verify={"ok": False, "reason": "empty candidate code"},
                typecheck_ok=False,
            )

        try:
            ast.parse(code)
            static_verify = {"ok": True, "reason": "AST parse ok"}
        except SyntaxError as exc:
            return VerificationResult(
                ok=False,
                confidence=0.2,
                runtime={"ok": False, "returncode": 1, "stdout": "", "stderr": str(exc)},
                static_verify={"ok": False, "reason": f"AST parse failed: {exc}"},
                typecheck_ok=False,
            )

        def _run_checks():
            with tempfile.TemporaryDirectory(prefix="termorganism_fast_mode_") as td:
                temp_path = Path(td) / original.name
                temp_path.write_text(code, encoding="utf-8")

                try:
                    repro = run_python_file(str(temp_path))
                    runtime = repro.to_dict() if hasattr(repro, "to_dict") else {
                        "ok": False,
                        "returncode": 1,
                        "stdout": "",
                        "stderr": "unknown runtime result",
                    }
                except Exception as exc:
                    runtime = {
                        "ok": False,
                        "returncode": 1,
                        "stdout": "",
                        "stderr": str(exc),
                    }

                pyc = subprocess.run(
                    ["python3", "-m", "py_compile", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                typecheck_ok = False
                if shutil.which("mypy"):
                    try:
                        mypy = subprocess.run(
                            ["mypy", "--ignore-missing-imports", str(temp_path)],
                            capture_output=True,
                            text=True,
                            timeout=3,
                        )
                        typecheck_ok = mypy.returncode == 0
                    except Exception:
                        typecheck_ok = False

                ok = (pyc.returncode == 0) and (runtime.get("returncode") == 0)
                confidence = 0.55 if ok else 0.25
                if ok and typecheck_ok:
                    confidence = 0.85
                elif ok:
                    confidence = 0.75

                return ok, confidence, runtime, {"ok": pyc.returncode == 0, "reason": pyc.stderr or "py_compile ok"}, typecheck_ok

        ok, confidence, runtime, static_verify2, typecheck_ok = await asyncio.to_thread(_run_checks)
        return VerificationResult(
            ok=ok,
            confidence=confidence,
            runtime=runtime,
            static_verify=static_verify2 if static_verify2 else static_verify,
            typecheck_ok=typecheck_ok,
        )


import re
