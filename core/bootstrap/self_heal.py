from __future__ import annotations

import importlib
import py_compile
import re
import sys
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CRITICAL_RELATIVE_PATHS = [
    "termorganism",
    "core/cli/autofix_cli.py",
    "core/autofix.py",
    "core/ui/thoughts.py",
    "core/ui/rich_sink.py",
    "core/verify/__init__.py",
    "core/verify/microvm.py",
    "core/verify/sandbox_router.py",
]


@dataclass
class CompileFailure:
    file_path: str
    line_no: int | None
    message: str
    exception_type: str


@dataclass
class HealAction:
    file_path: str
    action: str
    changed: bool
    detail: str


@dataclass
class HealReport:
    ok_before: bool
    ok_after: bool
    failures_before: list[dict[str, Any]]
    failures_after: list[dict[str, Any]]
    actions: list[dict[str, Any]]


def _critical_files() -> list[Path]:
    out = []
    for rel in CRITICAL_RELATIVE_PATHS:
        p = ROOT / rel
        if p.exists():
            out.append(p)
    return out


def _parse_line_no(msg: str) -> int | None:
    patterns = [
        r"line (\d+)",
        r"\((?:[^\n]*?), line (\d+)\)",
    ]
    for pat in patterns:
        m = re.search(pat, msg)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def preflight_compile(paths: list[Path] | None = None) -> list[CompileFailure]:
    failures: list[CompileFailure] = []
    for p in paths or _critical_files():
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as exc:
            failures.append(
                CompileFailure(
                    file_path=str(p),
                    line_no=_parse_line_no(str(exc)),
                    message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
    return failures


def _write_if_changed(path: Path, old: str, new: str) -> bool:
    if new == old:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _fix_literal_escaped_newlines(path: Path) -> HealAction:
    text = path.read_text(encoding="utf-8")
    changed = False
    new = text

    if "\\n" in text and text.count("\n") <= 3:
        if ("import " in text or "from " in text or "def " in text) and "\\n" in text:
            new = text.replace("\\n", "\n")
            changed = new != text

    return HealAction(
        file_path=str(path),
        action="fix_literal_escaped_newlines",
        changed=_write_if_changed(path, text, new) if changed else False,
        detail="converted literal \\n sequences into real newlines" if changed else "not applicable",
    )


def _fix_literal_backref_lines(path: Path) -> HealAction:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    filtered = [ln for ln in lines if not re.match(r"^\s*\\\d+\s+.*$", ln)]
    new = "\n".join(filtered) + ("\n" if text.endswith("\n") else "")
    changed = new != text

    return HealAction(
        file_path=str(path),
        action="fix_literal_backref_lines",
        changed=_write_if_changed(path, text, new) if changed else False,
        detail="removed literal regex backreference artifact lines" if changed else "not applicable",
    )


def _fix_verify_init_newline_export(path: Path) -> HealAction:
    text = path.read_text(encoding="utf-8")
    changed = False
    new = text
    if path.as_posix().endswith("core/verify/__init__.py") and "\\n" in text:
        new = (
            "from core.verify.microvm import SandboxConfig, SandboxResult, execute_python_in_sandbox_sync\n"
            "from core.verify.sandbox_router import build_sandbox_config, run_isolated_python_code\n"
        )
        changed = True

    return HealAction(
        file_path=str(path),
        action="fix_verify_init_newline_export",
        changed=_write_if_changed(path, text, new) if changed else False,
        detail="rewrote broken __init__ export block" if changed else "not applicable",
    )


def _fix_autofix_cli_try_block(path: Path) -> HealAction:
    text = path.read_text(encoding="utf-8")
    if not path.as_posix().endswith("core/cli/autofix_cli.py"):
        return HealAction(str(path), "fix_autofix_cli_try_block", False, "not applicable")

    lines = text.splitlines()
    n = len(lines)

    try_i = None
    for i, line in enumerate(lines):
        if line == "    try:":
            window = "\n".join(lines[i:i+50])
            if "_call_run_autofix_compat" in window and "sandbox_backend" in window:
                try_i = i
                break

    if try_i is None:
        return HealAction(str(path), "fix_autofix_cli_try_block", False, "try block not found")

    call_i = None
    for i in range(try_i + 1, min(n, try_i + 60)):
        if "_call_run_autofix_compat(" in lines[i]:
            call_i = i
            break

    if call_i is None:
        return HealAction(str(path), "fix_autofix_cli_try_block", False, "call block not found")

    balance = 0
    call_end = None
    for i in range(call_i, n):
        s = lines[i].lstrip()
        balance += s.count("(") - s.count(")")
        if balance <= 0 and s.endswith(")"):
            call_end = i
            break

    if call_end is None:
        return HealAction(str(path), "fix_autofix_cli_try_block", False, "call block end not found")

    call_block = [("        " + lines[i].lstrip()) for i in range(call_i, call_end + 1)]

    replacement = [
        "    try:",
        '        if getattr(args, "sandbox_backend", None):',
        '            os.environ["TERMORGANISM_SANDBOX_BACKEND"] = str(args.sandbox_backend)',
        '        if getattr(args, "sandbox_timeout", None) is not None:',
        '            os.environ["TERMORGANISM_SANDBOX_TIMEOUT"] = str(args.sandbox_timeout)',
        '        if getattr(args, "sandbox_memory_mb", None) is not None:',
        '            os.environ["TERMORGANISM_SANDBOX_MEMORY_MB"] = str(args.sandbox_memory_mb)',
    ] + call_block

    new_lines = lines[:try_i] + replacement + lines[call_end + 1:]
    new = "\n".join(new_lines) + "\n"
    changed = new != text

    return HealAction(
        file_path=str(path),
        action="fix_autofix_cli_try_block",
        changed=_write_if_changed(path, text, new) if changed else False,
        detail="rebuilt broken try/sandbox env/_call_run_autofix_compat block" if changed else "not applicable",
    )


def _fix_missing_stdlib_imports(path: Path) -> HealAction:
    text = path.read_text(encoding="utf-8")
    changed = False
    new = text

    if path.as_posix().endswith("core/autofix.py"):
        if "re.finditer(" in text and not re.search(r"^import re$", text, flags=re.M):
            if "import os\n" in new:
                new = new.replace("import os\n", "import os\nimport re\n", 1)
            elif "import asyncio\n" in new:
                new = new.replace("import asyncio\n", "import asyncio\nimport re\n", 1)
            else:
                new = "import re\n" + new
            changed = True

    return HealAction(
        file_path=str(path),
        action="fix_missing_stdlib_imports",
        changed=_write_if_changed(path, text, new) if changed else False,
        detail="added missing stdlib import(s)" if changed else "not applicable",
    )


def attempt_common_repairs(path: Path) -> list[HealAction]:
    actions = [
        _fix_literal_escaped_newlines(path),
        _fix_literal_backref_lines(path),
        _fix_verify_init_newline_export(path),
        _fix_autofix_cli_try_block(path),
        _fix_missing_stdlib_imports(path),
    ]
    return actions


def heal_until_stable(max_rounds: int = 3) -> HealReport:
    failures_before = preflight_compile()
    actions: list[HealAction] = []

    if not failures_before:
        return HealReport(
            ok_before=True,
            ok_after=True,
            failures_before=[],
            failures_after=[],
            actions=[],
        )

    seen = set()
    current_failures = failures_before

    for _ in range(max_rounds):
        changed_any = False
        for failure in current_failures:
            p = Path(failure.file_path)
            if not p.exists():
                continue
            key = (str(p), failure.line_no, failure.message)
            if key in seen:
                continue
            seen.add(key)
            file_actions = attempt_common_repairs(p)
            actions.extend(file_actions)
            if any(a.changed for a in file_actions):
                changed_any = True

        current_failures = preflight_compile()
        if not current_failures or not changed_any:
            break

    failures_after = current_failures
    return HealReport(
        ok_before=False,
        ok_after=not failures_after,
        failures_before=[asdict(x) for x in failures_before],
        failures_after=[asdict(x) for x in failures_after],
        actions=[asdict(x) for x in actions],
    )


def _import_main():
    importlib.invalidate_caches()
    mod = importlib.import_module("core.cli.autofix_cli")
    return getattr(mod, "main")


def bootstrap_then_run_main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    failures = preflight_compile()
    if failures:
        report = heal_until_stable()
        if not report.ok_after:
            sys.stderr.write("[bootstrap-self-heal] unable to restore critical files\n")
            sys.stderr.write(str(asdict(report)) + "\n")
            return 2

    try:
        main = _import_main()
        return int(main(argv) if callable(main) else 1)
    except TypeError:
        # Some existing main() implementations do not accept argv.
        try:
            main = _import_main()
            return int(main() if callable(main) else 1)
        except Exception:
            pass
    except Exception as exc:
        # One extra self-heal attempt if import/runtime still dies during bootstrap.
        report = heal_until_stable()
        if report.ok_after:
            try:
                main = _import_main()
                try:
                    return int(main(argv) if callable(main) else 1)
                except TypeError:
                    return int(main() if callable(main) else 1)
            except Exception:
                pass
        sys.stderr.write("[bootstrap-self-heal] bootstrap retry failed\n")
        sys.stderr.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return 3

# ----------------------------------------------------------------------
# import-graph aware override for critical file discovery
# ----------------------------------------------------------------------

def _critical_files() -> list[Path]:
    try:
        from core.bootstrap.preflight import discover_critical_files
        files = discover_critical_files(ROOT)
        if files:
            return files
    except Exception:
        pass

    out = []
    for rel in CRITICAL_RELATIVE_PATHS:
        p = ROOT / rel
        if p.exists():
            out.append(p)
    return out
