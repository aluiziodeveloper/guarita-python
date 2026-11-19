"""Porta para o modelo de linguagem do agente e o adaptador do Ollama."""

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

type Message = dict[str, Any]
type ToolSpec = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class ChatModel(Protocol):
    async def chat(self, messages: list[Message], tools: list[ToolSpec]) -> ModelReply: ...


class OllamaChat:
    """Fala com a API /api/chat do Ollama, sem streaming."""

    def __init__(self, client: httpx.AsyncClient, model: str, temperature: float = 0.0) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature

    async def chat(self, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        response = await self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "think": False,
                "options": {"temperature": self._temperature},
            },
        )
        response.raise_for_status()
        message = response.json()["message"]
        calls = [
            ToolCall(name=call["function"]["name"], arguments=call["function"]["arguments"])
            for call in message.get("tool_calls") or []
        ]
        return ModelReply(content=message.get("content", ""), tool_calls=calls)
