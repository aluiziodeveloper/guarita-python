"""Pipeline configurável de inspetores de ida e de volta por rota de ferramenta."""

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass

from mcp.types import CallToolResult

from guarita.domain import Call, Decision
from guarita.gate import Gate
from guarita.response import ResultReviewer


@dataclass(frozen=True)
class RoutePipeline:
    inbound: tuple[Gate, ...] = ()
    outbound: tuple[ResultReviewer, ...] = ()

    async def decide(self, call: Call) -> Decision:
        for gate in self.inbound:
            decision = await gate.decide(call)
            if not decision.allowed:
                return decision
        return Decision.allow()

    async def review(self, call: Call, result: CallToolResult) -> CallToolResult:
        current = result
        for reviewer in self.outbound:
            current = await reviewer.review(call, current)
            if current.is_error:
                return current
        return current


class PipelineRouter:
    """Seleciona o pipeline da rota da ferramenta e atua como Gate e ResultReviewer."""

    def __init__(
        self,
        routes: Mapping[str, RoutePipeline] | None = None,
        default: RoutePipeline | None = None,
    ) -> None:
        self._routes = dict(routes or {})
        self._default = default or RoutePipeline()

    def _for_tool(self, tool_name: str) -> RoutePipeline:
        for pattern, pipeline in self._routes.items():
            if fnmatch.fnmatchcase(tool_name, pattern):
                return pipeline
        return self._default

    async def decide(self, call: Call) -> Decision:
        return await self._for_tool(call.tool).decide(call)

    async def review(self, call: Call, result: CallToolResult) -> CallToolResult:
        return await self._for_tool(call.tool).review(call, result)
