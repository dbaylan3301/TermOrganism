from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/experts/shell_runtime.py": '''from __future__ import annotations

import re
from pathlib import Path


class ShellRuntimeExpert:
    name = "shell_runtime"

    COMMON_COMMAND_PACKAGES = {
        "rg": "ripgrep",
        "fd": "fd-find or fd",
        "bat": "bat",
        "fzf": "fzf",
        "eza": "eza",
        "jq": "jq",
        "yq": "yq",
        "tree": "tree",
        "htop": "htop",
        "ncdu": "ncdu",
        "uv": "uv",
        "poetry": "poetry",
        "pipx": "pipx",
        "pnpm": "pnpm",
        "bun": "bun",
        "deno": "deno",
    }

    def _extract_missing_command(self, error_text: str) -> str | None:
        patterns = [
            r"bash:\\s*([^:\\n]+): command not found",
            r"zsh:\\s*command not found:\\s*([^\\n]+)",
            r"/bin/sh:\\s*([^:\\n]+): not found",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "", flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_permission_target(self, error_text: str) -> str | None:
        patterns = [
            r"Permission denied:?\\s*['\\"]?([^'\\"]+)['\\"]?",
            r"cannot execute:?\\s*['\\"]?([^'\\"]+)['\\"]?",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "", flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_missing_path(self, error_text: str) -> str | None:
        patterns = [
            r"No such file or directory:?\\s*['\\"]?([^'\\"]+)['\\"]?",
            r"cannot access ['\\"]?([^'\\"]+)['\\"]?: No such file or directory",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "", flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _command_not_found_candidate(self, cmd: str):
        package_hint = self.COMMON_COMMAND_PACKAGES.get(cmd)
        summary = f"Shell command not found: {cmd}"

        suggestions = [
            f"command -v {cmd}",
            f"which {cmd}",
            f"echo $PATH",
        ]

        install_hint = None
        if package_hint:
            install_hint = package_hint
            suggestions.extend([
                f"sudo apt install {package_hint}",
                f"pkg install {package_hint}",
                f"brew install {package_hint}",
            ])

        return {
            "expert": self.name,
            "kind": "shell_command_missing",
            "confidence": 0.76 if package_hint else 0.64,
            "summary": summary,
            "patch": None,
            "candidate_code": "",
            "metadata": {
                "missing_command": cmd,
                "package_hint": install_hint,
                "suggestions": suggestions,
                "rationale": "missing shell executable detected from stderr signature",
            },
        }

    def _permission_denied_candidate(self, target: str | None):
        target = target or "./<target>"
        suggestions = [
            f"ls -l {target}",
            f"chmod +x {target}",
            f"./{Path(target).name}" if "/" not in target else target,
        ]

        return {
            "expert": self.name,
            "kind": "shell_permission_denied",
            "confidence": 0.72,
            "summary": f"Permission denied while executing/accessing: {target}",
            "patch": f"chmod +x {target}",
            "candidate_code": "",
            "metadata": {
                "target": target,
                "suggestions": suggestions,
                "rationale": "shell permission failure detected",
            },
        }

    def _missing_path_candidate(self, missing_path: str):
        parent = str(Path(missing_path).parent)
        suggestions = [
            f"ls -la {parent}" if parent not in ("", ".") else "pwd",
            f"mkdir -p {parent}" if parent not in ("", ".") else None,
            f"touch {missing_path}",
        ]
        suggestions = [x for x in suggestions if x]

        return {
            "expert": self.name,
            "kind": "shell_missing_path",
            "confidence": 0.68,
            "summary": f"Shell path missing: {missing_path}",
            "patch": suggestions[-1] if suggestions else None,
            "candidate_code": "",
            "metadata": {
                "missing_path": missing_path,
                "suggestions": suggestions,
                "rationale": "shell path/file missing detected",
            },
        }

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""

        missing_cmd = self._extract_missing_command(error_text)
        if missing_cmd:
            return [self._command_not_found_candidate(missing_cmd)]

        permission_target = self._extract_permission_target(error_text)
        if "permission denied" in error_text.lower():
            return [self._permission_denied_candidate(permission_target)]

        missing_path = self._extract_missing_path(error_text)
        if missing_path:
            return [self._missing_path_candidate(missing_path)]

        return [{
            "expert": self.name,
            "kind": "shell_runtime",
            "confidence": 0.40,
            "summary": "Shell/runtime oriented repair suggestion",
            "patch": None,
            "candidate_code": "",
            "metadata": {
                "rationale": "generic shell runtime fallback",
            },
        }]
''',

    "test_shell_runtime_only.py": '''#!/usr/bin/env python3
from core.engine.context_builder import build_context
from core.experts.shell_runtime import ShellRuntimeExpert

expert = ShellRuntimeExpert()

cases = [
    "zsh: command not found: bat",
    "bash: rg: command not found",
    "Permission denied: ./run.sh",
    "ls: cannot access 'logs/app.log': No such file or directory",
]

for error_text in cases:
    ctx = build_context(error_text=error_text)
    out = expert.propose(ctx)
    print("=" * 72)
    print(error_text)
    print(out)
''',
}


def backup_and_write(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(
            path.read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
        )
        print(f"[BACKUP] {rel_path} -> {backup.relative_to(ROOT)}")

    path.write_text(content, encoding="utf-8")
    print(f"[WRITE]  {rel_path}")


def main() -> int:
    for rel_path, content in PATCHES.items():
        backup_and_write(rel_path, content)

    print("\\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
