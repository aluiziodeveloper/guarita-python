"""Credencial dedicada por servidor a montante: fim do confused deputy (token passthrough)."""

from collections.abc import Mapping
from typing import Any

import httpx
from mcp.types import CallToolResult, ListToolsResult


class CredentialError(ValueError):
    """Servidor a montante sem credencial configurada (falha fechada)."""


class CredentialVault:
    """Mantém uma credencial isolada por servidor, nunca repassando o token do usuário."""

    def __init__(self, credentials_by_server: Mapping[str, str]) -> None:
        self._creds = {k: v for k, v in credentials_by_server.items() if v.strip()}

    def for_server(self, server: str) -> str:
        cred = self._creds.get(server)
        if cred is None:
            raise CredentialError(f"servidor sem credencial dedicada: {server}")
        return cred


class UpstreamHttpClient:
    """Cliente HTTP para um servidor MCP usando apenas a credencial própria daquele servidor."""

    def __init__(
        self,
        base_url: str,
        server_name: str,
        vault: CredentialVault,
        http: httpx.AsyncClient,
    ) -> None:
        self._url = base_url.rstrip("/") + "/mcp"
        self._server = server_name
        self._vault = vault
        self._http = http

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._vault.for_server(self._server)}"}

    async def list_tools(self) -> ListToolsResult:
        resp = await self._http.post(
            self._url, headers=self._headers(), json={"method": "tools/list"}
        )
        resp.raise_for_status()
        return ListToolsResult.model_validate(resp.json())

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        resp = await self._http.post(
            self._url,
            headers=self._headers(),
            json={"method": "tools/call", "params": {"name": name, "arguments": arguments or {}}},
        )
        resp.raise_for_status()
        return CallToolResult.model_validate(resp.json())
