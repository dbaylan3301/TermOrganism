from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.mimo.llm.base import LLMMessage, LLMResponse
from core.mimo.llm.groq import GroqProvider
from core.mimo.llm.openai import OpenAIProvider
from core.mimo.llm.anthropic import AnthropicProvider
from core.mimo.llm.ollama import OllamaProvider


def _make_httpx_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ── Groq ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_groq_provider_chat():
    provider = GroqProvider(api_key="test-key", model="llama-3.3-70b-versatile")
    mock_resp = _make_httpx_response({
        "choices": [{"message": {"content": "Hello from Groq!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "llama-3.3-70b-versatile",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="Hi")])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from Groq!"
    assert result.model == "llama-3.3-70b-versatile"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    provider._client.post.assert_called_once()
    call_args = provider._client.post.call_args
    assert call_args[0][0] == "/chat/completions"
    await provider.close()


@pytest.mark.asyncio
async def test_groq_provider_chat_tool_calls():
    provider = GroqProvider(api_key="test-key", model="llama-3.3-70b-versatile")
    mock_resp = _make_httpx_response({
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "search",
                        "arguments": json.dumps({"query": "test"}),
                    },
                }],
            },
        }],
        "usage": {},
        "model": "llama-3.3-70b-versatile",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="search")])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["id"] == "call_1"
    assert result.tool_calls[0]["name"] == "search"
    assert result.tool_calls[0]["arguments"] == {"query": "test"}
    await provider.close()


# ── OpenAI ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_provider_chat():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4.1")
    mock_resp = _make_httpx_response({
        "choices": [{"message": {"content": "Hello from OpenAI!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "gpt-4.1",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="Hi")])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from OpenAI!"
    assert result.model == "gpt-4.1"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    provider._client.post.assert_called_once()
    call_args = provider._client.post.call_args
    assert call_args[0][0] == "/chat/completions"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_provider_chat_tool_calls():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4.1")
    mock_resp = _make_httpx_response({
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "/tmp/test"}),
                    },
                }],
            },
        }],
        "usage": {},
        "model": "gpt-4.1",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="read file")])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "read_file"
    assert result.tool_calls[0]["arguments"] == {"path": "/tmp/test"}
    await provider.close()


# ── Anthropic ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_provider_chat():
    provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
    mock_resp = _make_httpx_response({
        "content": [{"type": "text", "text": "Hello from Anthropic!"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "claude-sonnet-4-20250514",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="Hi")])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from Anthropic!"
    assert result.model == "claude-sonnet-4-20250514"
    assert result.usage == {"input_tokens": 10, "output_tokens": 5}
    provider._client.post.assert_called_once()
    call_args = provider._client.post.call_args
    assert call_args[0][0] == "/v1/messages"
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_provider_chat_tool_calls():
    provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
    mock_resp = _make_httpx_response({
        "content": [
            {"type": "text", "text": "Let me search."},
            {"type": "tool_use", "id": "toolu_1", "name": "search", "input": {"query": "test"}},
        ],
        "usage": {},
        "model": "claude-sonnet-4-20250514",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="search")])

    assert result.content == "Let me search."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["id"] == "toolu_1"
    assert result.tool_calls[0]["name"] == "search"
    assert result.tool_calls[0]["arguments"] == {"query": "test"}
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_provider_system_message():
    provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
    mock_resp = _make_httpx_response({
        "content": [{"type": "text", "text": "OK"}],
        "usage": {},
        "model": "claude-sonnet-4-20250514",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    messages = [
        LLMMessage(role="system", content="You are helpful."),
        LLMMessage(role="user", content="Hi"),
    ]
    await provider.chat(messages)

    call_kwargs = provider._client.post.call_args[1]["json"]
    assert call_kwargs["system"] == "You are helpful."
    assert len(call_kwargs["messages"]) == 1
    assert call_kwargs["messages"][0]["role"] == "user"
    await provider.close()


# ── Ollama ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_provider_chat():
    provider = OllamaProvider(model="llama3.1:70b")
    mock_resp = _make_httpx_response({
        "message": {"content": "Hello from Ollama!"},
        "eval_count": 42,
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="Hi")])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from Ollama!"
    assert result.model == "llama3.1:70b"
    assert result.usage == {"total_tokens": 42}
    provider._client.post.assert_called_once()
    call_args = provider._client.post.call_args
    assert call_args[0][0] == "/api/chat"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_chat_tool_calls():
    provider = OllamaProvider(model="llama3.1:70b")
    mock_resp = _make_httpx_response({
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "grep_search",
                    "arguments": json.dumps({"pattern": "TODO"}),
                },
            }],
        },
        "eval_count": 0,
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="grep")])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "grep_search"
    assert result.tool_calls[0]["arguments"] == {"pattern": "TODO"}
    assert result.tool_calls[0]["id"].startswith("call_")
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_tool_calls_dict_arguments():
    provider = OllamaProvider(model="llama3.1:70b")
    mock_resp = _make_httpx_response({
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "bash",
                    "arguments": {"command": "ls"},
                },
            }],
        },
        "eval_count": 0,
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.chat([LLMMessage(role="user", content="ls")])

    assert result.tool_calls[0]["arguments"] == {"command": "ls"}
    await provider.close()


# ── Payload verification ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_groq_sends_tools_in_payload():
    provider = GroqProvider(api_key="test-key")
    mock_resp = _make_httpx_response({
        "choices": [{"message": {"content": "ok"}}],
        "usage": {},
        "model": "llama-3.3-70b-versatile",
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    tools = [{"type": "function", "function": {"name": "foo", "parameters": {}}}]
    await provider.chat([LLMMessage(role="user", content="x")], tools=tools)

    call_kwargs = provider._client.post.call_args[1]["json"]
    assert call_kwargs["tools"] == tools
    assert call_kwargs["tool_choice"] == "auto"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_sends_payload_with_options():
    provider = OllamaProvider(model="llama3.1:70b")
    mock_resp = _make_httpx_response({
        "message": {"content": "ok"},
        "eval_count": 0,
    })
    provider._client.post = AsyncMock(return_value=mock_resp)

    await provider.chat(
        [LLMMessage(role="user", content="x")],
        temperature=0.3,
        max_tokens=512,
    )

    call_kwargs = provider._client.post.call_args[1]["json"]
    assert call_kwargs["options"]["temperature"] == 0.3
    assert call_kwargs["options"]["num_predict"] == 512
    assert call_kwargs["stream"] is False
    await provider.close()
