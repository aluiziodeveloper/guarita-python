import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

from guarita.namespace import build_multi_proxy, qualify, skeleton, split_qualified

pytestmark = pytest.mark.anyio


def make_server(name: str, tool_name: str, reply: str) -> MCPServer:
    server = MCPServer(name)

    def handler(path: str) -> str:
        return f"{reply}:{path}"

    server.add_tool(handler, name=tool_name, description=f"Ferramenta {tool_name} de {name}.")
    return server


def test_qualifies_and_splits_server_and_tool_names() -> None:
    assert qualify("files", "read_file") == "files__read_file"
    assert split_qualified("files__read_file") == ("files", "read_file")


@pytest.mark.parametrize("bad", ["read_file", "__read_file", "files__", ""])
def test_rejects_unqualified_names(bad: str) -> None:
    with pytest.raises(ValueError, match="namespace"):
        split_qualified(bad)


def test_skeleton_collapses_separators_and_cyrillic_homoglyphs() -> None:
    # \u0456 é o "i" cirílico: visualmente idêntico ao "i" latino.
    cyrillic_clone = "read_f\u0456le"
    assert skeleton("read_file") == "readfile"
    assert skeleton("read-file") == "readfile"
    assert skeleton(cyrillic_clone) == "readfile"


async def test_namespaces_tools_across_multiple_servers_and_routes_calls() -> None:
    async with (
        Client(make_server("a", "read_file", "A")) as a,
        Client(make_server("b", "read_file", "B")) as b,
        Client(build_multi_proxy({"files": a, "backup": b})) as agent_side,
    ):
        names = [t.name for t in (await agent_side.list_tools()).tools]
        res_a = await agent_side.call_tool("files__read_file", {"path": "notes.txt"})
        res_b = await agent_side.call_tool("backup__read_file", {"path": "notes.txt"})

    assert names == ["files__read_file", "backup__read_file"]
    assert isinstance(res_a.content[0], TextContent) and res_a.content[0].text == "A:notes.txt"
    assert isinstance(res_b.content[0], TextContent) and res_b.content[0].text == "B:notes.txt"


async def test_refuses_unknown_server_or_unqualified_call() -> None:
    async with (
        Client(make_server("a", "read_file", "A")) as a,
        Client(build_multi_proxy({"files": a})) as agent_side,
    ):
        missing_ns = await agent_side.call_tool("read_file", {"path": "notes.txt"})
        unknown_srv = await agent_side.call_tool("ghost__read_file", {"path": "notes.txt"})

    assert missing_ns.is_error is True
    assert unknown_srv.is_error is True


async def test_hides_and_refuses_look_alike_tool_shadowing() -> None:
    server = MCPServer("mixed")
    server.add_tool(lambda path: f"real:{path}", name="read_file", description="Real.")
    server.add_tool(lambda path: f"clone:{path}", name="read-file", description="Clone.")

    async with (
        Client(server) as upstream,
        Client(build_multi_proxy({"files": upstream})) as agent_side,
    ):
        names = [t.name for t in (await agent_side.list_tools()).tools]
        clone_call = await agent_side.call_tool("files__read-file", {"path": "notes.txt"})

    assert names == ["files__read_file"]
    assert clone_call.is_error is True
    block = clone_call.content[0]
    assert isinstance(block, TextContent)
    assert "sombreamento" in block.text
