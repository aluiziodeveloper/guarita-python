"""Impressão digital canônica da definição de uma ferramenta."""

import hashlib
import json
from typing import Any

from mcp.types import Tool

# O que o modelo lê e o que a chamada aceita: mudou qualquer um, mudou a ferramenta.
FIELDS = ("name", "title", "description", "inputSchema", "outputSchema", "annotations")


def canonical(tool: Tool) -> str:
    data: dict[str, Any] = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
    kept = {key: data[key] for key in FIELDS if key in data}
    return json.dumps(kept, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(tool: Tool) -> str:
    return hashlib.sha256(canonical(tool).encode("utf-8")).hexdigest()
