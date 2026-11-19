"""O proxy MCP: para o agente, a Guarita é um servidor; para o servidor, um cliente."""

from typing import Any, Protocol

from mcp.server import Server, ServerRequestContext
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams


class Upstream(Protocol):
    """O servidor MCP de verdade, do outro lado da Guarita."""

    async def list_tools(self) -> ListToolsResult: ...

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult: ...


def build_proxy(upstream: Upstream) -> Server[Any]:
    async def list_tools(
        ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return await upstream.list_tools()

    async def call_tool(
        ctx: ServerRequestContext[Any], params: CallToolRequestParams
    ) -> CallToolResult:
        return await upstream.call_tool(params.name, params.arguments)

    return Server("guarita", on_list_tools=list_tools, on_call_tool=call_tool)
