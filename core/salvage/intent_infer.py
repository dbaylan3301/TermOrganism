from __future__ import annotations

def infer_intent(source: str, imports: list[str], defs: list[str]) -> dict:
    text = source.lower()
    tags: list[str] = []

    if "argparse" in imports or "click" in imports:
        tags.append("cli")
    if "requests" in imports or "aiohttp" in imports:
        tags.append("network_client")
    if "telegram" in text or "telebot" in text:
        tags.append("bot")
    if "ccxt" in imports or "binance" in text:
        tags.append("trading")
    if "flask" in imports or "fastapi" in imports:
        tags.append("web_app")
    if "pandas" in imports or "csv" in imports:
        tags.append("data_pipeline")
    if any(x in defs for x in ["main", "run", "start"]):
        tags.append("script_entrypoint")

    if not tags:
        tags.append("generic_python_script")

    return {
        "tags": tags,
        "summary": ", ".join(tags),
    }
