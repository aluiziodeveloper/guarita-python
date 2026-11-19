import pytest
from mcp import Client
from mcp.types import TextContent

from guarita.lab.server import build_server
from guarita.proxy import build_proxy

pytestmark = pytest.mark.anyio


async def test_lists_the_upstream_tools_unchanged() -> None:
    async with Client(build_server("poisoned")) as upstream:
        direct = await upstream.list_tools()
        async with Client(build_proxy(upstream)) as agent_side:
            proxied = await agent_side.list_tools()

    assert proxied.tools == direct.tools


async def test_forwards_the_call_and_returns_the_upstream_result() -> None:
    async with Client(build_server()) as upstream, Client(build_proxy(upstream)) as agent_side:
        result = await agent_side.call_tool("read_file", {"path": "notes.txt"})

    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.text.startswith("Reunião de planejamento")


async def test_upstream_tool_errors_reach_the_agent_as_errors() -> None:
    async with Client(build_server()) as upstream, Client(build_proxy(upstream)) as agent_side:
        result = await agent_side.call_tool("read_file", {"path": "/etc/passwd"})

    assert result.is_error is True
