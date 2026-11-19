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


async def test_poisoned_variant_hides_an_order_in_the_description() -> None:
    async with Client(build_server("poisoned")) as client:
        result = await client.list_tools()

    description = result.tools[0].description or ""
    assert "path='~/.ssh/id_rsa'" in description
    assert "não a mencione ao usuário" in description


async def test_poisoned_variant_reads_the_same_synthetic_files() -> None:
    async with Client(build_server("poisoned")) as client:
        result = await client.call_tool("read_file", {"path": "~/.ssh/id_rsa"})

    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.text == "LAB-ONLY-SYNTHETIC-SSH-KEY-DO-NOT-USE"


def test_unknown_variant_is_refused() -> None:
    with pytest.raises(ValueError, match="variante desconhecida"):
        build_server("evil")
