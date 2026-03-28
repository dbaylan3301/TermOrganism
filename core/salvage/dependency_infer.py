from __future__ import annotations

import sys

PACKAGE_MAP = {
    "yaml": "PyYAML",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "Crypto": "pycryptodome",
    "dotenv": "python-dotenv",
    "telegram": "python-telegram-bot",
    "telebot": "pyTelegramBotAPI",
    "requests": "requests",
    "rich": "rich",
    "numpy": "numpy",
    "pandas": "pandas",
    "aiohttp": "aiohttp",
    "websockets": "websockets",
    "ccxt": "ccxt",
    "flask": "Flask",
    "fastapi": "fastapi",
}

STDLIB = set(getattr(sys, "stdlib_module_names", set())) | {
    "os", "sys", "json", "re", "math", "time", "pathlib", "typing",
    "subprocess", "itertools", "functools", "collections", "logging",
    "argparse", "asyncio", "datetime", "hashlib", "tempfile", "shutil",
    "dataclasses", "unittest", "threading", "queue", "csv",
}

def infer_dependencies(imports: list[str]) -> dict:
    third_party: list[str] = []
    unresolved: list[str] = []

    for mod in imports:
        root = mod.split(".")[0]
        if root in STDLIB:
            continue
        pkg = PACKAGE_MAP.get(root)
        if pkg:
            if pkg not in third_party:
                third_party.append(pkg)
        else:
            if root not in unresolved:
                unresolved.append(root)

    return {
        "third_party": sorted(third_party),
        "unresolved_modules": sorted(unresolved),
    }
