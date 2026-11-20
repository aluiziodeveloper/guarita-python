"""Validação estrita de argumentos contra o JSON Schema fixado no catálogo."""

from typing import Any

from guarita.catalog import PinCatalog
from guarita.domain import Call, Decision


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


class SchemaGate:
    """Recusa campos faltantes, tipos errados e argumentos extras fora do schema fixado."""

    def __init__(self, catalog: PinCatalog, server: str) -> None:
        self._catalog = catalog
        self._server = server

    async def decide(self, call: Call) -> Decision:
        definition = self._catalog.definition(self._server, call.tool)
        if definition is None:
            return Decision.deny(f"esquema ausente no catálogo para {call.tool}")
        schema: dict[str, Any] = definition.get("inputSchema") or {}
        properties: dict[str, Any] = schema.get("properties") or {}
        required: list[str] = schema.get("required") or []

        for req in required:
            if req not in call.arguments:
                return Decision.deny(f"argumento obrigatório ausente: {req}")
        for key, value in call.arguments.items():
            if key not in properties:
                return Decision.deny(f"argumento inesperado fora do esquema: {key}")
            expected = properties[key].get("type")
            if isinstance(expected, str) and not _matches_type(value, expected):
                return Decision.deny(f"tipo inválido para {key}: esperado {expected}")
        return Decision.allow()
