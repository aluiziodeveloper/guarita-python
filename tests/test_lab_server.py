import pytest
from mcp import Client
from mcp.types import TextContent

from guarita.lab.server import build_server

pytestmark = pytest.mark.anyio


async def test_lists_read_file_with_its_description() -> None:
    async with Client(build_server()) as client:
        result = await client.list_tools()

    assert [tool.name for tool in result.tools] == ["read_file"]
    assert result.tools[0].description == "Lê um arquivo de texto do projeto e devolve o conteúdo."


async def test_read_file_returns_the_synthetic_content() -> None:
    async with Client(build_server()) as client:
        result = await client.call_tool("read_file", {"path": "notes.txt"})

    assert result.is_error is False
    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.text.startswith("Reunião de planejamento")


async def test_unknown_file_is_a_tool_error() -> None:
    async with Client(build_server()) as client:
        result = await client.call_tool("read_file", {"path": "/etc/passwd"})

    assert result.is_error is True
