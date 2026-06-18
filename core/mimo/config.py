from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG_PATH = Path.home() / ".termorganism" / "config.yaml"


class Config:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    @property
    def llm_provider(self) -> str:
        return self.get("llm.default_provider", "openai")

    @property
    def openai_api_key(self) -> str:
        import os
        return self.get("llm.providers.openai.api_key", "") or os.environ.get("OPENAI_API_KEY", "")

    @property
    def openai_model(self) -> str:
        return self.get("llm.providers.openai.model", "gpt-4.1")

    @property
    def openai_base_url(self) -> str:
        return self.get("llm.providers.openai.base_url", "https://api.openai.com/v1")

    @property
    def anthropic_api_key(self) -> str:
        import os
        return self.get("llm.providers.anthropic.api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def anthropic_model(self) -> str:
        return self.get("llm.providers.anthropic.model", "claude-sonnet-4-20250514")

    @property
    def groq_api_key(self) -> str:
        import os
        return self.get("llm.providers.groq.api_key", "") or os.environ.get("GROQ_API_KEY", "")

    @property
    def groq_model(self) -> str:
        return self.get("llm.providers.groq.model", "llama-3.3-70b-versatile")

    @property
    def ollama_base_url(self) -> str:
        return self.get("llm.providers.ollama.base_url", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        return self.get("llm.providers.ollama.model", "llama3.1:70b")

    @property
    def max_tokens(self) -> int:
        return int(self.get("llm.max_tokens", 16384))

    @property
    def temperature(self) -> float:
        return float(self.get("llm.temperature", 0.7))

    @property
    def theme(self) -> str:
        return self.get("ui.theme", "mimo")


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
