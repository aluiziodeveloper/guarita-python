"""O proxy MCP: para o agente, a Guarita é um servidor; para o servidor, um cliente."""

from typing import Any, Protocol

from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from guarita.domain import Call, Decision, InvalidCallError
from guarita.gate import AllowAll, Gate
from guarita.integrity import PinnedTools
from guarita.response import ResultReviewer
from guarita.scanner import DescriptionScanner


class Upstream(Protocol):
    """O servidor MCP de verdade, do outro lado da Guarita."""

    async def list_tools(self) -> ListToolsResult: ...

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult: ...


def refusal(reason: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=f"Guarita: chamada negada ({reason})")],
        is_error=True,
    )


def build_proxy(
    upstream: Upstream,
    gate: Gate | None = None,
    integrity: PinnedTools | None = None,
    scanner: DescriptionScanner | None = None,
    reviewer: ResultReviewer | None = None,
) -> Server[Any]:
    gate = gate or AllowAll()

    def check_tool(tool: Tool) -> Decision:
        if integrity is not None:
            checked = integrity.check(tool)
            if not checked.allowed:
                return checked
        if scanner is not None:
            scanned = scanner.check(tool)
            if not scanned.allowed:
                return scanned
        return Decision.allow()

    async def list_tools(
        ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        listing = await upstream.list_tools()
        if integrity is None and scanner is None:
            return listing
        # O agente nem chega a ler uma definição que não passou na integridade ou no varredor.
        kept = [tool for tool in listing.tools if check_tool(tool).allowed]
        return ListToolsResult(tools=kept)

    async def call_tool(
        ctx: ServerRequestContext[Any], params: CallToolRequestParams
    ) -> CallToolResult:
        try:
            call = Call(params.name, params.arguments or {})
        except InvalidCallError as error:
            return refusal(str(error))
        if integrity is not None or scanner is not None:
            listing = await upstream.list_tools()
            current = next((t for t in listing.tools if t.name == call.tool), None)
            if current is None:
                return refusal(f"{call.tool} não existe no servidor")
            checked = check_tool(current)
            if not checked.allowed:
                return refusal(checked.reason)
        decision = await gate.decide(call)
        if not decision.allowed:
            return refusal(decision.reason)
        result = await upstream.call_tool(call.tool, dict(call.arguments))
        if reviewer is not None:
            return await reviewer.review(call, result)
        return result

    return Server("guarita", on_list_tools=list_tools, on_call_tool=call_tool)
