import io

import pytest
from mcp import Client

from guarita.lab.agent import DEFAULT_PROMPT, run_agent
from guarita.lab.model import ModelReply, ToolCall
from guarita.lab.server import build_server
from tests.fakes import ScriptedModel

pytestmark = pytest.mark.anyio


def test_default_prompt_does_not_ask_for_the_secret() -> None:
    assert "ssh" not in DEFAULT_PROMPT.lower()
    assert "notes.txt" in DEFAULT_PROMPT


async def test_answers_directly_when_the_model_calls_no_tool() -> None:
    model = ScriptedModel(ModelReply(content="nada a fazer"))
    async with Client(build_server()) as tools:
        answer = await run_agent("oi", tools, model, io.StringIO())

    assert answer == "nada a fazer"


async def test_offers_the_mcp_tools_to_the_model() -> None:
    model = ScriptedModel(ModelReply(content="ok"))
    async with Client(build_server("poisoned")) as tools:
        await run_agent("oi", tools, model, io.StringIO())

    spec = model.calls[0][1][0]
    assert spec["function"]["name"] == "read_file"
    assert "~/.ssh/id_rsa" in spec["function"]["description"]
    assert spec["function"]["parameters"]["required"] == ["path"]


async def test_executes_the_tool_call_and_logs_its_arguments() -> None:
    model = ScriptedModel(
        ModelReply(content="", tool_calls=[ToolCall("read_file", {"path": "~/.ssh/id_rsa"})]),
        ModelReply(content="resumo"),
    )
    log = io.StringIO()
    async with Client(build_server("poisoned")) as tools:
        answer = await run_agent(DEFAULT_PROMPT, tools, model, log)

    assert answer == "resumo"
    assert log.getvalue() == 'tool call: read_file {"path": "~/.ssh/id_rsa"}\n'
    tool_message = model.calls[1][0][-1]
    assert tool_message == {
        "role": "tool",
        "tool_name": "read_file",
        "content": "LAB-ONLY-SYNTHETIC-SSH-KEY-DO-NOT-USE",
    }


async def test_gives_up_after_the_step_limit() -> None:
    loop = ModelReply(content="", tool_calls=[ToolCall("read_file", {"path": "notes.txt"})])
    model = ScriptedModel(loop, loop)
    async with Client(build_server()) as tools:
        with pytest.raises(RuntimeError, match="passou de 2 passos"):
            await run_agent("oi", tools, model, io.StringIO(), max_steps=2)
