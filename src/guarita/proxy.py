"""O proxy MCP: para o agente, a Guarita é um servidor; para o servidor, um cliente."""

from typing import Any, Protocol

from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
)

from guarita.domain import Call, InvalidCallError
from guarita.gate import AllowAll, Gate


class Upstream(Protocol):
    """O servidor MCP de verdade, do outro lado da Guarita."""

    async def list_tools(self) -> ListToolsResult: ...

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult: ...


def refusal(reason: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=f"Guarita: chamada negada ({reason})")],
        is_error=True,
    )


def build_proxy(upstream: Upstream, gate: Gate | None = None) -> Server[Any]:
    gate = gate or AllowAll()

    async def list_tools(
        ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return await upstream.list_tools()

    async def call_tool(
        ctx: ServerRequestContext[Any], params: CallToolRequestParams
    ) -> CallToolResult:
        try:
            call = Call(params.name, params.arguments or {})
        except InvalidCallError as error:
            return refusal(str(error))
        decision = await gate.decide(call)
        if not decision.allowed:
            return refusal(decision.reason)
        return await upstream.call_tool(call.tool, dict(call.arguments))

    return Server("guarita", on_list_tools=list_tools, on_call_tool=call_tool)
