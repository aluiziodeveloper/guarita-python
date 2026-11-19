import json
from collections.abc import Mapping

import httpx
import pytest

from guarita.lab.model import ModelReply, OllamaChat, ToolCall

pytestmark = pytest.mark.anyio


def ollama_returning(
    message: Mapping[str, object], seen: list[dict[str, object]]
) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message": message, "done": True})

    return httpx.AsyncClient(base_url="http://ollama.test", transport=httpx.MockTransport(handler))


async def test_sends_model_messages_and_tools_without_streaming() -> None:
    seen: list[dict[str, object]] = []
    async with ollama_returning({"role": "assistant", "content": "ok"}, seen) as client:
        await OllamaChat(client, "qwen3:1.7b").chat([{"role": "user", "content": "oi"}], [])

    assert seen == [
        {
            "model": "qwen3:1.7b",
            "messages": [{"role": "user", "content": "oi"}],
            "tools": [],
            "stream": False,
            "think": False,
            "options": {"temperature": 0.0},
        }
    ]


async def test_reads_the_tool_calls_of_the_reply() -> None:
    message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "notes.txt"}}}],
    }
    async with ollama_returning(message, []) as client:
        reply = await OllamaChat(client, "qwen3:1.7b").chat([], [])

    assert reply == ModelReply(
        content="", tool_calls=[ToolCall("read_file", {"path": "notes.txt"})]
    )


async def test_reply_without_tool_calls_has_an_empty_list() -> None:
    async with ollama_returning({"role": "assistant", "content": "resumo"}, []) as client:
        reply = await OllamaChat(client, "qwen3:1.7b").chat([], [])

    assert reply == ModelReply(content="resumo")
