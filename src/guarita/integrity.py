"""Integridade: só passa a ferramenta cuja definição atual é a mesma que foi aprovada."""

from mcp.types import Tool

from guarita.catalog import PinCatalog
from guarita.domain import Decision
from guarita.fingerprint import fingerprint


class PinnedTools:
    def __init__(self, catalog: PinCatalog, server: str) -> None:
        self._catalog = catalog
        self._server = server

    def check(self, tool: Tool) -> Decision:
        pinned = self._catalog.pinned(self._server, tool.name)
        if pinned is None:
            return Decision.deny(f"{tool.name} não está no catálogo de {self._server}")
        if pinned != fingerprint(tool):
            return Decision.deny(f"a definição de {tool.name} mudou desde a aprovação")
        return Decision.allow()
