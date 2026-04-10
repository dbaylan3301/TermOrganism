from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from core.watch.predictive_runtime import analyze_python_text


@dataclass(slots=True)
class TextEditSpec:
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    new_text: str


@dataclass(slots=True)
class CodeActionSpec:
    action_id: str
    title: str
    kind: str
    auto_apply: bool
    diagnostic_kind: str
    message: str
    edit: dict[str, Any] | None
    edits: list[dict[str, Any]] | None
    preview: str


def _action_id(file_path: str, title: str, kind: str, line: int) -> str:
    raw = f"{file_path}|{title}|{kind}|{line}".encode("utf-8", "ignore")
    return hashlib.sha1(raw).hexdigest()[:12]


def _make_action(
    *,
    file_path: str,
    title: str,
    kind: str,
    auto_apply: bool,
    diagnostic_kind: str,
    message: str,
    line: int,
    edit: TextEditSpec | None = None,
    edits: list[TextEditSpec] | None = None,
    preview: str = "",
) -> CodeActionSpec:
    return CodeActionSpec(
        action_id=_action_id(file_path, title, diagnostic_kind, line),
        title=title,
        kind=kind,
        auto_apply=auto_apply,
        diagnostic_kind=diagnostic_kind,
        message=message,
        edit=asdict(edit) if edit else None,
        edits=[asdict(x) for x in (edits or [])] or None,
        preview=preview,
    )


def _line_text(lines: list[str], line_1based: int) -> str:
    idx = max(0, line_1based - 1)
    return lines[idx] if idx < len(lines) else ""


def _line_col_to_offset(text: str, line_1based: int, col: int) -> int:
    lines = text.splitlines(keepends=True)

    if line_1based <= 1:
        return max(0, col)

    if line_1based > len(lines) + 1:
        return len(text)

    if line_1based == len(lines) + 1:
        return len(text)

    return sum(len(lines[i]) for i in range(line_1based - 1)) + max(0, col)


def _apply_single_edit(text: str, edit: dict[str, Any]) -> str:
    start = _line_col_to_offset(text, int(edit["start_line"]), int(edit["start_col"]))
    end = _line_col_to_offset(text, int(edit["end_line"]), int(edit["end_col"]))
    return text[:start] + str(edit["new_text"]) + text[end:]


def _apply_edits_to_text(text: str, edits: list[dict[str, Any]]) -> str:
    ordered = sorted(
        edits,
        key=lambda e: (
            int(e["start_line"]),
            int(e["start_col"]),
            int(e["end_line"]),
            int(e["end_col"]),
        ),
        reverse=True,
    )
    out = text
    for edit in ordered:
        out = _apply_single_edit(out, edit)
    return out


def _find_function_signature_line(lines: list[str], func_name: str) -> tuple[int, str] | None:
    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith(f"def {func_name}(") or stripped.startswith(f"async def {func_name}("):
            return idx, line
    return None


def _build_mutable_default_fix(text: str, lines: list[str], func_name: str, default_line: int, message: str, file_path: str) -> CodeActionSpec | None:
    sig = _find_function_signature_line(lines, func_name)
    if not sig:
        return None

    sig_line_no, sig_line = sig
    if "[" in sig_line:
        new_sig = sig_line.replace("=[]", "=None").replace("= []", "=None")
        target_init = "[]"
    elif "{}" in sig_line:
        new_sig = sig_line.replace("={}", "=None").replace("= {}", "=None")
        target_init = "{}"
    elif "set()" in sig_line:
        new_sig = sig_line.replace("=set()", "=None").replace("= set()", "=None")
        target_init = "set()"
    else:
        return None

    indent = sig_line[:len(sig_line) - len(sig_line.lstrip())]
    body_indent = indent + "    "

    param_name = None
    # kaba ama güvenli: a=None ise a bul
    try:
        left = new_sig.split("(", 1)[1].rsplit(")", 1)[0]
        for part in left.split(","):
            if "=None" in part:
                param_name = part.split("=", 1)[0].strip().lstrip("*")
                break
    except Exception:
        param_name = None

    if not param_name:
        return None

    insertion_line = sig_line_no + 1
    init_line = f"{body_indent}if {param_name} is None:\n{body_indent}    {param_name} = {target_init}\n"

    edits = [
        TextEditSpec(
            start_line=sig_line_no,
            start_col=0,
            end_line=sig_line_no,
            end_col=len(sig_line),
            new_text=new_sig,
        ),
        TextEditSpec(
            start_line=insertion_line,
            start_col=0,
            end_line=insertion_line,
            end_col=0,
            new_text=init_line,
        ),
    ]

    preview = _apply_edits_to_text(text, [asdict(x) for x in edits])
    return _make_action(
        file_path=file_path,
        title="Apply mutable default safe rewrite",
        kind="quickfix",
        auto_apply=True,
        diagnostic_kind="mutable-default-risk",
        message=message,
        line=default_line,
        edits=edits,
        preview=preview,
    )


def _build_main_guard_fix(text: str, lines: list[str], line: int, message: str, file_path: str) -> CodeActionSpec | None:
    if 'if __name__ == "__main__":' in text or "if __name__ == '__main__':" in text:
        return None

    # güvenli ve minimal: sadece dosya sonuna guard skeleton ekle
    insertion_line = len(lines) + 1
    guard = '\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
    edits = [
        TextEditSpec(
            start_line=insertion_line,
            start_col=0,
            end_line=insertion_line,
            end_col=0,
            new_text=guard,
        )
    ]
    preview = _apply_edits_to_text(text, [asdict(x) for x in edits])
    return _make_action(
        file_path=file_path,
        title="Append __main__ guard",
        kind="quickfix",
        auto_apply=True,
        diagnostic_kind="main-guard-risk",
        message=message,
        line=line,
        edits=edits,
        preview=preview,
    )


def _build_path_guard_fix(text: str, lines: list[str], line: int, message: str, file_path: str) -> CodeActionSpec | None:
    original = _line_text(lines, line)
    if "open(" not in original or "with open(" not in original:
        return None

    indent = original[:len(original) - len(original.lstrip())]

    # sadece literal string path ve with open için güvenli şablon
    import_line_needed = "from pathlib import Path" not in text
    edit_list: list[TextEditSpec] = []

    if import_line_needed:
        edit_list.append(
            TextEditSpec(
                start_line=1,
                start_col=0,
                end_line=1,
                end_col=0,
                new_text="from pathlib import Path\n",
            )
        )

    guarded = (
        f"{indent}if not Path(PATH_PLACEHOLDER).exists():\n"
        f"{indent}    raise FileNotFoundError(PATH_PLACEHOLDER)\n"
        f"{original}"
    )

    # original içinden string literal yakala
    import re
    m = re.search(r"""open\((["'][^"']+["'])\)""", original)
    if not m:
        m = re.search(r"""open\((["'][^"']+["'])\s*,""", original)
    if not m:
        return None
    path_literal = m.group(1)
    guarded = guarded.replace("PATH_PLACEHOLDER", path_literal)

    edit_list.append(
        TextEditSpec(
            start_line=line,
            start_col=0,
            end_line=line,
            end_col=len(original),
            new_text=guarded,
        )
    )

    preview = _apply_edits_to_text(text, [asdict(x) for x in edit_list])
    return _make_action(
        file_path=file_path,
        title="Apply path existence guard",
        kind="quickfix",
        auto_apply=True,
        diagnostic_kind="path-risk",
        message=message,
        line=line,
        edits=edit_list,
        preview=preview,
    )


def build_code_actions_for_text(text: str, *, file_path: str) -> dict[str, Any]:
    payload = analyze_python_text(text, file_path=file_path)
    diagnostics = payload.get("diagnostics", [])
    lines = text.splitlines()
    actions: list[CodeActionSpec] = []

    # AST names for mutable-default
    func_names: dict[int, str] = {}
    try:
        import ast
        tree = ast.parse(text, filename=file_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in list(node.args.defaults or []):
                    if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                        func_names[getattr(d, "lineno", 0)] = node.name
    except Exception:
        pass

    for d in diagnostics:
        kind = str(d.get("kind", ""))
        line = int(d.get("line", 1))
        message = str(d.get("message", ""))

        if kind == "bare-except-risk":
            original = _line_text(lines, line)
            indent = original[:len(original) - len(original.lstrip())]
            new_line = indent + "except Exception:"
            edit = TextEditSpec(
                start_line=line,
                start_col=0,
                end_line=line,
                end_col=len(original),
                new_text=new_line,
            )
            preview = _apply_edits_to_text(text, [asdict(edit)])
            actions.append(_make_action(
                file_path=file_path,
                title="Replace bare except with except Exception",
                kind="quickfix",
                auto_apply=True,
                diagnostic_kind=kind,
                message=message,
                line=line,
                edit=edit,
                preview=preview,
            ))

        elif kind == "mutable-default-risk":
            func_name = func_names.get(line)
            if func_name:
                action = _build_mutable_default_fix(text, lines, func_name, line, message, file_path)
                if action:
                    actions.append(action)
            actions.append(_make_action(
                file_path=file_path,
                title="Preview mutable default fix",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: mutable default arg yerine None kullan; fonksiyon başında if arg is None: arg = [] / {} / set() deseni uygula.",
            ))

        elif kind == "import-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview guarded import strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: try/except ImportError guard, opsiyonel dependency fallback veya explicit install path ekle.",
            ))

        elif kind == "path-risk":
            auto = _build_path_guard_fix(text, lines, line, message, file_path)
            if auto:
                actions.append(auto)
            actions.append(_make_action(
                file_path=file_path,
                title="Preview path guard strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: open() öncesi Path.exists() guard, fallback path ya da user-facing hata mesajı ekle.",
            ))

        elif kind == "eval-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview eval replacement strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: eval yerine ast.literal_eval, map-dispatch veya explicit parser kullan.",
            ))

        elif kind == "exec-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview exec replacement strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: exec yerine explicit function dispatch, plugin registry veya sandboxed interpreter kullan.",
            ))

        elif kind == "subprocess-shell-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview shell=False subprocess strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: shell=True yerine arg listesi ver ve shell=False kullan.",
            ))

        elif kind == "wildcard-import-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview explicit import list",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: wildcard import yerine kullanılan sembolleri explicit listele.",
            ))

        elif kind == "main-guard-risk":
            auto = _build_main_guard_fix(text, lines, line, message, file_path)
            if auto:
                actions.append(auto)
            actions.append(_make_action(
                file_path=file_path,
                title='Preview __main__ guard',
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview='Öneri: if __name__ == "__main__": guard ekle ve CLI girişini onun içine taşı.',
            ))

        elif kind == "env-default-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview getenv default/fail-fast strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview='Öneri: os.getenv("KEY", default) kullan ya da None için açık fail-fast kontrolü ekle.',
            ))

        elif kind == "relative-import-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview package-safe import strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: relative import yerine package entrypoint, absolute import veya module execution strategy kullan.",
            ))

        elif kind == "secret-inline-risk":
            actions.append(_make_action(
                file_path=file_path,
                title="Preview secret externalization strategy",
                kind="refactor.rewrite",
                auto_apply=False,
                diagnostic_kind=kind,
                message=message,
                line=line,
                preview="Öneri: inline secret yerine env var, secret manager veya ignored local config kullan.",
            ))

    return {
        "file": file_path,
        "diagnostics": diagnostics,
        "actions": [asdict(x) for x in actions],
    }


def apply_action_to_file(file_path: str, action_id: str) -> dict[str, Any]:
    path = Path(file_path).expanduser().resolve()
    text = path.read_text(encoding="utf-8", errors="ignore")
    payload = build_code_actions_for_text(text, file_path=str(path))

    for action in payload["actions"]:
        if action["action_id"] != action_id:
            continue

        if not action["auto_apply"]:
            return {
                "ok": False,
                "reason": "action is preview-only",
                "action": action,
            }

        edits = []
        if action.get("edits"):
            edits = action["edits"]
        elif action.get("edit"):
            edits = [action["edit"]]
        else:
            return {
                "ok": False,
                "reason": "no edit payload",
                "action": action,
            }

        new_text = _apply_edits_to_text(text, edits)
        path.write_text(new_text, encoding="utf-8")
        return {
            "ok": True,
            "reason": "applied",
            "action": action,
        }

    return {
        "ok": False,
        "reason": "action not found",
    }
