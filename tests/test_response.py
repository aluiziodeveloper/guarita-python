import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from guarita.domain import Call
from guarita.lab.server import build_server
from guarita.proxy import build_proxy, refusal
from guarita.response import extract_text

pytestmark = pytest.mark.anyio


class BlockWordReviewer:
    def __init__(self, word: str) -> None:
        self._word = word

    async def review(self, call: Call, result: CallToolResult) -> CallToolResult:
        if self._word in extract_text(result).lower():
            return refusal(f"resposta bloqueada em {call.tool}")
        return result


async def test_proxy_reviews_tool_results_before_returning_to_agent() -> None:
    reviewer = BlockWordReviewer("ignore")
    async with (
        Client(build_server()) as upstream,
        Client(build_proxy(upstream, reviewer=reviewer)) as agent_side,
    ):
        clean = await agent_side.call_tool("read_file", {"path": "notes.txt"})
        poisoned = await agent_side.call_tool("read_file", {"path": "ticket.txt"})

    assert clean.is_error is False
    assert poisoned.is_error is True
    block = poisoned.content[0]
    assert isinstance(block, TextContent)
    assert block.text == "Guarita: chamada negada (resposta bloqueada em read_file)"
