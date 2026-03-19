import re

def fix_indentation_after_colon(code: str):
    lines = code.splitlines(True)
    changed = False
    out = []
    for i, line in enumerate(lines):
        if i > 0 and lines[i-1].rstrip().endswith(":"):
            stripped = line.lstrip()
            if stripped and not line.startswith((" ", "\t")):
                out.append("    " + line)
                changed = True
                continue
        out.append(line)
    return "".join(out), changed

def fix_tabs(code: str):
    if "\t" not in code:
        return code, False
    return code.replace("\t", "    "), True

def fix_py2_print(code: str):
    pat = re.compile(r'(?m)^(\s*)print\s+"([^"]*)"\s*$')
    new = pat.sub(r'\1print("\2")', code)
    return new, new != code

def fix_missing_colon(code: str):
    lines = code.splitlines(True)
    changed = False
    out = []
    starters = ("def ", "class ", "if ", "elif ", "else", "for ", "while ", "try", "except", "finally", "with ")
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.endswith(":"):
            if any(stripped.startswith(s) for s in starters):
                out.append(line.rstrip("\n") + ":\n")
                changed = True
                continue
        out.append(line)
    return "".join(out), changed

def fix_unbalanced_quotes(code: str):
    if code.count('"') % 2 == 1:
        return code + '"\n', True
    return code, False

def fix_unbalanced_parens(code: str):
    opens = code.count("(")
    closes = code.count(")")
    if opens > closes:
        return code + (")" * (opens - closes)) + "\n", True
    return code, False

def apply_local_repairs(code: str):
    steps = []
    confidence = "none"

    for name, fn, conf in [
        ("tabs-to-spaces", fix_tabs, "high"),
        ("python2-print", fix_py2_print, "high"),
        ("missing-colon", fix_missing_colon, "medium"),
        ("indentation-after-colon", fix_indentation_after_colon, "high"),
        ("unbalanced-quotes", fix_unbalanced_quotes, "medium"),
        ("unbalanced-parens", fix_unbalanced_parens, "medium"),
    ]:
        code2, changed = fn(code)
        if changed:
            code = code2
            steps.append(name)
            if confidence == "none":
                confidence = conf
            elif confidence == "medium" and conf == "high":
                confidence = "high"

    return {
        "code": code,
        "changed": bool(steps),
        "steps": steps,
        "confidence": confidence,
    }
