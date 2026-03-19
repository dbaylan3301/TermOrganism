import ast

def verify_python(code: str):
    try:
        ast.parse(code)
        return {"ok": True, "reason": "AST parse ok"}
    except Exception as e:
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
