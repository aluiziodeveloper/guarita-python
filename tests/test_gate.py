import io

import pytest
from mcp import Client
from mcp.types import TextContent

from guarita.domain import Call
from guarita.gate import ArgumentAllowlist
from guarita.lab.agent import DEFAULT_PROMPT, run_agent
from guarita.lab.model import ModelReply, ToolCall
from guarita.lab.server import build_server
from guarita.proxy import build_proxy
from tests.fakes import ScriptedModel

pytestmark = pytest.mark.anyio

ONLY_NOTES = ArgumentAllowlist("read_file", "path", ["notes.txt"])


@pytest.mark.parametrize(
    ("call", "allowed"),
    [
        (Call("read_file", {"path": "notes.txt"}), True),
        (Call("read_file", {"path": "~/.ssh/id_rsa"}), False),
        (Call("read_file", {}), False),
        (Call("list_dir", {"path": "/"}), True),
    ],
)
async def test_allowlist_decides_by_the_argument(call: Call, allowed: bool) -> None:
    assert (await ONLY_NOTES.decide(call)).allowed is allowed


async def test_denied_call_never_reaches_the_server() -> None:
    async with (
        Client(build_server()) as upstream,
        Client(build_proxy(upstream, ONLY_NOTES)) as agent_side,
    ):
        result = await agent_side.call_tool("read_file", {"path": "~/.ssh/id_rsa"})

    assert result.is_error is True
    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.text == (
        "Guarita: chamada negada (path='~/.ssh/id_rsa' fora da lista de read_file)"
    )


async def test_malformed_call_is_refused_at_the_edge() -> None:
    async with Client(build_server()) as upstream, Client(build_proxy(upstream)) as agent_side:
        result = await agent_side.call_tool("read file", {"path": "notes.txt"})

    assert result.is_error is True
    block = result.content[0]
    assert isinstance(block, TextContent)
    assert "nome de ferramenta inválido" in block.text


async def test_the_poisoned_agent_gets_a_refusal_instead_of_the_key() -> None:
    model = ScriptedModel(
        ModelReply(content="", tool_calls=[ToolCall("read_file", {"path": "~/.ssh/id_rsa"})]),
        ModelReply(content="resumo"),
    )
    async with (
        Client(build_server("poisoned")) as upstream,
        Client(build_proxy(upstream, ONLY_NOTES)) as agent_side,
    ):
        await run_agent(DEFAULT_PROMPT, agent_side, model, io.StringIO())

    tool_message = model.calls[1][0][-1]
    assert "LAB-ONLY-SYNTHETIC-SSH-KEY" not in tool_message["content"]
    assert tool_message["content"].startswith("Guarita: chamada negada")
