from __future__ import annotations
#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class HotCacheExtractor:
    def __init__(self, benchmark_dir: Path = Path("benchmarks/results")):
        self.benchmark_dir = benchmark_dir
        self.patterns: dict[str, dict[str, Any]] = {}

    def extract_all(self):
        files = []
        files.extend(sorted(self.benchmark_dir.glob("case_*.json")))
        files.extend(sorted(self.benchmark_dir.glob("case_results*.json")))

        for case_file in files:
            self._process_file(case_file)

        self._generate_hot_force_py()

    def _process_file(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._process_case(item)
        elif isinstance(data, dict):
            # single case
            if any(k in data for k in ("success", "ok", "candidate_code", "repair_code", "failure_signature")):
                self._process_case(data)

            # nested collections
            for key in ("cases", "results", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._process_case(item)

    def _process_case(self, data: dict[str, Any]):
        if not self._is_success(data):
            return

        confidence = self._extract_confidence(data)
        if confidence < 0.9:
            return

        signature = self._extract_signature(data)
        repair_code = self._extract_repair_code(data)
        if not signature or not repair_code:
            return

        strategy = (
            str(data.get("repair_strategy") or "")
            or str((data.get("result") or {}).get("metadata", {}).get("strategy") or "")
            or str((data.get("result") or {}).get("kind") or "")
            or "generated"
        )

        description = (
            str(data.get("description") or "")
            or str((data.get("result") or {}).get("summary") or "")
            or str(data.get("summary") or "")
        )

        self.patterns[signature] = {
            "code": repair_code,
            "strategy": strategy,
            "confidence": round(confidence, 3),
            "description": description,
            "source": "benchmark_extracted",
        }
        print(f"✓ Extracted: {signature}")

    def _is_success(self, data: dict[str, Any]) -> bool:
        if bool(data.get("success")):
            return True
        if bool(data.get("ok")):
            return True

        verify = data.get("verify") or {}
        if isinstance(verify, dict) and bool(verify.get("ok")):
            return True

        contract = data.get("contract_result") or {}
        if isinstance(contract, dict) and bool(contract.get("ok")):
            return True

        branch = data.get("branch_result") or {}
        if isinstance(branch, dict) and bool(branch.get("ok")):
            return True

        result = data.get("result") or {}
        if isinstance(result, dict):
            branch2 = result.get("branch_result") or {}
            contract2 = result.get("contract_result") or {}
            if isinstance(branch2, dict) and bool(branch2.get("ok")):
                return True
            if isinstance(contract2, dict) and bool(contract2.get("ok")):
                return True

        return False

    def _extract_confidence(self, data: dict[str, Any]) -> float:
        conf = data.get("confidence")
        if isinstance(conf, (int, float)):
            return float(conf)
        if isinstance(conf, dict):
            try:
                return float(conf.get("score", 0.0) or 0.0)
            except Exception:
                return 0.0

        result = data.get("result") or {}
        if isinstance(result, dict):
            try:
                return float(result.get("confidence", 0.0) or 0.0)
            except Exception:
                return 0.0

        best_plan = data.get("best_plan") or {}
        if isinstance(best_plan, dict):
            try:
                return float(best_plan.get("confidence", 0.0) or 0.0)
            except Exception:
                return 0.0

        return 0.0

    def _extract_repair_code(self, data: dict[str, Any]) -> str:
        for key in ("repair_code", "candidate_code", "code"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val

        result = data.get("result") or {}
        if isinstance(result, dict):
            for key in ("repair_code", "candidate_code", "code"):
                val = result.get(key)
                if isinstance(val, str) and val.strip():
                    return val

        best_plan = data.get("best_plan") or {}
        if isinstance(best_plan, dict):
            edits = best_plan.get("edits") or []
            for edit in edits:
                if isinstance(edit, dict):
                    code = str(edit.get("candidate_code") or "")
                    if code.strip():
                        return code

        source_plan = ((data.get("result") or {}).get("source_plan") if isinstance(data.get("result"), dict) else {}) or {}
        if isinstance(source_plan, dict):
            edits = source_plan.get("edits") or []
            for edit in edits:
                if isinstance(edit, dict):
                    code = str(edit.get("candidate_code") or "")
                    if code.strip():
                        return code

        return ""

    def _extract_signature(self, data: dict[str, Any]) -> str:
        explicit = str(data.get("failure_signature") or "").strip()
        if explicit:
            return explicit.lower()

        error_type = self._extract_error_type(data).lower()
        error_text = self._extract_error_text(data).lower()

        # high-value normalized signatures first
        if "filenotfounderror" in error_type or "filenotfounderror" in error_text:
            if "open(" in error_text or "read_text" in error_text or "no such file or directory" in error_text:
                return "filenotfounderror:open:runtime"

        if "modulenotfounderror" in error_type or "no module named" in error_text or "importerror" in error_text:
            return "importerror:no_module_named"

        cleaned = re.sub(r'file "[^"]+"', 'file "PATH"', error_text)
        cleaned = re.sub(r'line \d+', 'line N', cleaned)
        cleaned = re.sub(r'0x[0-9a-f]+', 'ADDR', cleaned)

        if not cleaned.strip():
            cleaned = json.dumps(data, sort_keys=True)[:1000].lower()

        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]
        prefix = error_type if error_type else "unknownerror"
        return f"{prefix}:{digest}"

    def _extract_error_type(self, data: dict[str, Any]) -> str:
        for key in ("failure_type", "error_type", "exception_type"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val

        result = data.get("result") or {}
        if isinstance(result, dict):
            branch = result.get("branch_result") or {}
            runtime = branch.get("runtime") or {}
            stderr = str(runtime.get("stderr") or "")
            m = re.search(r'([A-Za-z_][A-Za-z0-9_]*Error):', stderr)
            if m:
                return m.group(1)

        error_text = self._extract_error_text(data)
        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*Error):', error_text)
        if m:
            return m.group(1)

        return "UnknownError"

    def _extract_error_text(self, data: dict[str, Any]) -> str:
        for key in ("error_text", "error_message", "stderr", "message"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val

        repro = data.get("repro") or {}
        if isinstance(repro, dict):
            stderr = repro.get("stderr")
            if isinstance(stderr, str) and stderr.strip():
                return stderr

        result = data.get("result") or {}
        if isinstance(result, dict):
            branch = result.get("branch_result") or {}
            runtime = branch.get("runtime") or {}
            stderr = runtime.get("stderr")
            if isinstance(stderr, str) and stderr.strip():
                return stderr

        branch = data.get("branch_result") or {}
        if isinstance(branch, dict):
            runtime = branch.get("runtime") or {}
            stderr = runtime.get("stderr")
            if isinstance(stderr, str) and stderr.strip():
                return stderr

        return ""

    def _generate_hot_force_py(self):
        output = Path("core/orchestrator_hot_force_patterns.py")
        lines = []
        lines.append("# AUTO-GENERATED by scripts/extract_hot_patterns.py")
        lines.append(f"# {datetime.now().isoformat()}")
        lines.append(f"# Total patterns: {len(self.patterns)}")
        lines.append("")
        lines.append("HOT_REPAIRS = " + json.dumps(self.patterns, indent=2, ensure_ascii=False))
        lines.append("")
        signature_patterns = {}
        for sig in self.patterns:
            key = sig.split(":", 1)[0].lower()
            signature_patterns[key] = sig
        lines.append("SIGNATURE_PATTERNS = " + json.dumps(signature_patterns, indent=2, ensure_ascii=False))
        lines.append("")
        output.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✓ Generated {output} with {len(self.patterns)} patterns")


if __name__ == "__main__":
    HotCacheExtractor().extract_all()
