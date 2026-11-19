from pathlib import Path

import pytest
from mcp import Client
from mcp.types import TextContent

from guarita.catalog import PinCatalog
from guarita.integrity import PinnedTools
from guarita.lab.server import build_rug_pull_server, build_server
from guarita.proxy import build_proxy

pytestmark = pytest.mark.anyio


async def test_rug_pull_server_swaps_the_description_after_the_first_call() -> None:
    async with Client(build_rug_pull_server()) as server:
        before = (await server.list_tools()).tools[0].description or ""
        await server.call_tool("read_file", {"path": "notes.txt"})
        after = (await server.list_tools()).tools[0].description or ""

    assert "~/.ssh/id_rsa" not in before
    assert "~/.ssh/id_rsa" in after


async def test_unpinned_tools_are_hidden_and_refused(tmp_path: Path) -> None:
    with PinCatalog(tmp_path / "catalog.db") as catalog:
        integrity = PinnedTools(catalog, "files")
        async with (
            Client(build_server()) as upstream,
            Client(build_proxy(upstream, integrity=integrity)) as agent_side,
        ):
            listing = await agent_side.list_tools()
            result = await agent_side.call_tool("read_file", {"path": "notes.txt"})

    assert listing.tools == []
    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.text == "Guarita: chamada negada (read_file não está no catálogo de files)"


async def test_a_rug_pull_is_denied_after_the_swap(tmp_path: Path) -> None:
    with PinCatalog(tmp_path / "catalog.db") as catalog:
        async with Client(build_rug_pull_server()) as upstream:
            catalog.pin("files", (await upstream.list_tools()).tools)
            proxy = build_proxy(upstream, integrity=PinnedTools(catalog, "files"))
            async with Client(proxy) as agent_side:
                first = await agent_side.call_tool("read_file", {"path": "notes.txt"})
                listing = await agent_side.list_tools()
                second = await agent_side.call_tool("read_file", {"path": "notes.txt"})

    assert first.is_error is False
    assert listing.tools == []
    block = second.content[0]
    assert isinstance(block, TextContent)
    assert (
        block.text == "Guarita: chamada negada (a definição de read_file mudou desde a aprovação)"
    )
