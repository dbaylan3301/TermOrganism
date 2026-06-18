from __future__ import annotations

from typing import Any

from .base import BaseLLMProvider
from ..config import get_config


def create_provider(name: str | None = None) -> BaseLLMProvider:
    config = get_config()
    provider_name = name or config.llm_provider

    if provider_name == "groq":
        from .groq import GroqProvider
        return GroqProvider(
            api_key=config.groq_api_key,
            model=config.groq_model,
        )
    elif provider_name == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=config.openai_model,
            base_url=config.openai_base_url,
        )
    elif provider_name == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )
    elif provider_name == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def list_providers() -> list[str]:
    return ["groq", "openai", "anthropic", "ollama"]
