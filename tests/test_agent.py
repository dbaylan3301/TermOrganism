from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.mimo.agent import Agent
from core.mimo.llm.base import LLMMessage, LLMResponse


@pytest.fixture
def mock_deps():
    """Set up mocked dependencies for Agent."""
    mock_config = MagicMock()
    mock_config.temperature = 0.7
    mock_config.max_tokens = 16384

    mock_provider = AsyncMock()
    mock_provider.name = "test-provider"

    mock_registry = MagicMock()
    mock_registry.to_schemas.return_value = [{"type": "function", "function": {"name": "test"}}]
    mock_registry.execute = AsyncMock(return_value="tool result")

    mock_context = MagicMock()
    mock_context.get_system_prompt.return_value = "System prompt"

    mock_session = MagicMock()
    mock_session.get_messages.return_value = []
    mock_session.add_message = MagicMock()
    mock_session.clear = MagicMock()

    with patch("core.mimo.agent.get_config", return_value=mock_config), \
         patch("core.mimo.agent.create_provider", return_value=mock_provider), \
         patch("core.mimo.agent.create_default_registry", return_value=mock_registry), \
         patch("core.mimo.agent.AgentContext", return_value=mock_context), \
         patch("core.mimo.agent.SessionMemory", return_value=mock_session):
        agent = Agent()

    return agent, mock_provider, mock_registry, mock_context, mock_session


@pytest.mark.asyncio
async def test_agent_process_message(mock_deps):
    agent, mock_provider, _, _, mock_session = mock_deps

    mock_provider.chat.return_value = LLMResponse(content="Hello!")

    result = await agent.process("Hi there")

    assert result == "Hello!"
    mock_session.add_message.assert_any_call("user", "Hi there")
    mock_session.add_message.assert_any_call("assistant", "Hello!")
    mock_provider.chat.assert_called_once()


@pytest.mark.asyncio
async def test_agent_handles_tool_call(mock_deps):
    agent, mock_provider, mock_registry, _, mock_session = mock_deps

    tool_call_response = LLMResponse(
        content=None,
        tool_calls=[{"id": "tc_1", "name": "bash", "arguments": {"command": "ls"}}]
    )
    final_response = LLMResponse(content="Done!")

    mock_provider.chat.side_effect = [tool_call_response, final_response]

    result = await agent.process("List files")

    assert result == "Done!"
    mock_registry.execute.assert_called_once_with("bash", command="ls")
    assert mock_provider.chat.call_count == 2


@pytest.mark.asyncio
async def test_agent_no_response(mock_deps):
    agent, mock_provider, _, _, _ = mock_deps

    mock_provider.chat.return_value = LLMResponse(content=None, tool_calls=None)

    result = await agent.process("test")

    assert result == "(no response)"


@pytest.mark.asyncio
async def test_agent_max_turns(mock_deps):
    agent, mock_provider, mock_registry, _, _ = mock_deps

    tool_call_response = LLMResponse(
        content=None,
        tool_calls=[{"id": "tc_1", "name": "bash", "arguments": {"command": "loop"}}]
    )

    mock_provider.chat.return_value = tool_call_response
    agent._max_turns = 3

    result = await agent.process("loop forever")

    assert result == "(max turns reached)"
    assert mock_registry.execute.call_count == 3


@pytest.mark.asyncio
async def test_agent_callback(mock_deps):
    agent, mock_provider, _, _, _ = mock_deps

    tool_call_response = LLMResponse(
        content=None,
        tool_calls=[{"id": "tc_1", "name": "bash", "arguments": {"command": "echo"}}]
    )
    final_response = LLMResponse(content="Callback test done")

    mock_provider.chat.side_effect = [tool_call_response, final_response]

    callback = AsyncMock()
    result = await agent.process("test callback", callback=callback)

    assert result == "Callback test done"
    assert callback.call_count == 2
    callback.assert_any_await("tool_start", "bash", {"command": "echo"})
    callback.assert_any_await("tool_end", "bash", "tool result")


@pytest.mark.asyncio
async def test_agent_clear_session(mock_deps):
    agent, _, _, _, mock_session = mock_deps

    agent.clear_session()

    mock_session.clear.assert_called_once()