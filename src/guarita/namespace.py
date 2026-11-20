"""Namespace por servidor e defesa contra sombreamento (tool shadowing)."""

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    Tool,
)

from guarita.domain import Call, InvalidCallError
from guarita.gate import AllowAll, Gate
from guarita.integrity import PinnedTools
from guarita.proxy import Upstream, refusal
from guarita.scanner import DescriptionScanner

SEPARATOR = "__"

# Homóglifos comuns (cirílico e grego) que imitam letras latinas em nomes de ferramenta.
HOMOGLYPHS: dict[str, str] = {
    "\u0430": "a",  # cirílico a
    "\u0435": "e",  # cirílico e
    "\u0456": "i",  # cirílico i
    "\u043e": "o",  # cirílico o
    "\u0440": "p",  # cirílico p
    "\u0441": "c",  # cirílico c
    "\u0445": "x",  # cirílico x
    "\u03b1": "a",  # grego alfa
    "\u03bf": "o",  # grego ômicron
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def qualify(server: str, tool: str) -> str:
    if not server or not tool or SEPARATOR in server:
        raise ValueError(f"namespace inválido: {server!r}, {tool!r}")
    return f"{server}{SEPARATOR}{tool}"


def split_qualified(name: str) -> tuple[str, str]:
    server, sep, tool = name.partition(SEPARATOR)
    if not (sep and server and tool):
        raise ValueError(f"nome sem namespace '<servidor>__<ferramenta>': {name!r}")
    return server, tool


def skeleton(name: str) -> str:
    """Silhueta normalizada do nome: reduz homóglifos e separadores para achar clones."""
    normalized = unicodedata.normalize("NFKC", name).casefold()
    mapped = "".join(HOMOGLYPHS.get(ch, ch) for ch in normalized)
    return _NON_ALNUM.sub("", mapped)


def _select_safe_tools(
    server: str,
    tools: list[Tool],
    integrity: PinnedTools | None,
    scanner: DescriptionScanner | None,
) -> tuple[list[Tool], set[str]]:
    """Mantém só ferramentas aprovadas e sem sombreamento; devolve também os nomes bloqueados."""
    kept: list[Tool] = []
    shadowed: set[str] = set()
    seen_skeletons: dict[str, str] = {}
    for tool in tools:
        if integrity is not None and not integrity.check(tool).allowed:
            continue
        if scanner is not None and not scanner.check(tool).allowed:
            continue
        sk = skeleton(tool.name)
        if sk in seen_skeletons:
            shadowed.add(tool.name)
            continue
        seen_skeletons[sk] = tool.name
        kept.append(tool.model_copy(update={"name": qualify(server, tool.name)}))
    return kept, shadowed


def build_multi_proxy(
    upstreams: Mapping[str, Upstream],
    gate: Gate | None = None,
    integrity_by_server: Mapping[str, PinnedTools] | None = None,
    scanner: DescriptionScanner | None = None,
) -> Server[Any]:
    gate = gate or AllowAll()
    integrity_map = integrity_by_server or {}

    async def list_tools(
        ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        all_tools: list[Tool] = []
        for server_name, upstream in upstreams.items():
            listing = await upstream.list_tools()
            kept, _ = _select_safe_tools(
                server_name, listing.tools, integrity_map.get(server_name), scanner
            )
            all_tools.extend(kept)
        return ListToolsResult(tools=all_tools)

    async def call_tool(
        ctx: ServerRequestContext[Any], params: CallToolRequestParams
    ) -> CallToolResult:
        try:
            call = Call(params.name, params.arguments or {})
            server_name, raw_tool = split_qualified(call.tool)
        except (InvalidCallError, ValueError) as error:
            return refusal(str(error))
        upstream = upstreams.get(server_name)
        if upstream is None:
            return refusal(f"servidor desconhecido: {server_name}")
        listing = await upstream.list_tools()
        integrity = integrity_map.get(server_name)
        _, shadowed = _select_safe_tools(server_name, listing.tools, integrity, scanner)
        if raw_tool in shadowed:
            return refusal(f"sombreamento de nome detectado em {raw_tool}")
        current = next((t for t in listing.tools if t.name == raw_tool), None)
        if current is None:
            return refusal(f"{raw_tool} não existe em {server_name}")
        if integrity is not None:
            checked = integrity.check(current)
            if not checked.allowed:
                return refusal(checked.reason)
        if scanner is not None:
            scanned = scanner.check(current)
            if not scanned.allowed:
                return refusal(scanned.reason)
        decision = await gate.decide(call)
        if not decision.allowed:
            return refusal(decision.reason)
        return await upstream.call_tool(raw_tool, dict(call.arguments))

    return Server("guarita", on_list_tools=list_tools, on_call_tool=call_tool)
