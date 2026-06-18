import difflib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from local_repair import apply_local_repairs
from llm_repair import repair as llm_repair
from sandbox import run_python
from memory import log_repair

def context_for(file_path: str):
    p = Path(file_path).resolve().parent
    ctx = []
    if (p / "package.json").exists():
        ctx.append("node")
    if (p / "requirements.txt").exists() or (p / "pyproject.toml").exists() or (p / "setup.py").exists():
        ctx.append("python")
    if (p / "Cargo.toml").exists():
        ctx.append("rust")
    return ctx

def compile_check(file_path: str):
    p = subprocess.run(
        ["python3", "-m", "py_compile", file_path],
        capture_output=True,
        text=True
    )
    return p.returncode, p.stdout, p.stderr

def backup_file(file_path: str):
    src = Path(file_path)
    bak = src.with_name(src.name + ".bak")
    shutil.copy(src, bak)
    return bak

def show_diff(old: str, new: str, file_path: str):
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=file_path,
        tofile=file_path + ".fixed",
        lineterm=""
    )
    return "\n".join(diff)

def try_local_fix(file_path: str):
    src = Path(file_path).read_text(encoding="utf-8", errors="replace")
    result = apply_local_repairs(src)
    if not result["changed"]:
        return None

    Path(file_path).write_text(result["code"], encoding="utf-8")
    rc, out, err = run_python(file_path)
    if rc == 0:
        return {
            "ok": True,
            "strategy": "local",
            "confidence": result["confidence"],
            "steps": result["steps"],
            "code": result["code"],
            "diff": show_diff(src, result["code"], file_path),
        }

    Path(file_path).write_text(src, encoding="utf-8")
    return None

def try_llm_fix(file_path: str, error_text: str):
    src = Path(file_path).read_text(encoding="utf-8", errors="replace")
    ans = llm_repair(error_text, src)
    if not ans["ok"]:
        return {"ok": False, "reason": ans["reason"]}

    fixed = ans["fixed"]
    Path(file_path).write_text(fixed, encoding="utf-8")
    rc, out, err = run_python(file_path)
    if rc == 0:
        return {
            "ok": True,
            "strategy": "llm",
            "confidence": "medium",
            "steps": ["groq-repair"],
            "code": fixed,
            "diff": show_diff(src, fixed, file_path),
        }

    Path(file_path).write_text(src, encoding="utf-8")
    return {"ok": False, "reason": err or out or "sandbox failed"}

def fix(file_path: str):
    rc, out, err = compile_check(file_path)
    if rc == 0:
        return 0

    print("[organism] predicted failure")

    original = Path(file_path).read_text(encoding="utf-8", errors="replace")
    backup_file(file_path)

    local = try_local_fix(file_path)
    if local and local["ok"]:
        print(f"[organism] local repair matched: {', '.join(local['steps'])}")
        print(f"[organism] confidence: {local['confidence']}")
        print("[organism] sandbox passed")
        print(local["diff"])
        log_repair(file_path, "local", local["confidence"], True, context_for(file_path), local["steps"])
        return 0

    Path(file_path).write_text(original, encoding="utf-8")

    llm = try_llm_fix(file_path, err or out)
    if llm.get("ok"):
        print("[organism] consulting model")
        print("[organism] AI repair success")
        print(f"[organism] confidence: {llm['confidence']}")
        print("[organism] sandbox passed")
        print(llm["diff"])
        log_repair(file_path, "llm", llm["confidence"], True, context_for(file_path), llm["steps"])
        return 0

    print(f"[organism] AI repair failed: {llm.get('reason', 'unknown')}")
    log_repair(file_path, "llm", "low", False, context_for(file_path), [])
    return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: omega-autofix file.py")
        raise SystemExit(1)
    raise SystemExit(fix(sys.argv[1]))
