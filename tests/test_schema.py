from pathlib import Path

import pytest
from mcp.types import Tool

from guarita.catalog import PinCatalog
from guarita.domain import Call
from guarita.schema import SchemaGate

pytestmark = pytest.mark.anyio

SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "max_lines": {"type": "integer"},
    },
    "required": ["path"],
}


def make_catalog(tmp_path: Path) -> PinCatalog:
    catalog = PinCatalog(tmp_path / "catalog.db")
    catalog.pin("files", [Tool(name="read_file", description="Lê arquivo.", input_schema=SCHEMA)])
    return catalog


async def test_allows_arguments_matching_the_pinned_schema(tmp_path: Path) -> None:
    with make_catalog(tmp_path) as catalog:
        gate = SchemaGate(catalog, "files")
        decision = await gate.decide(Call("read_file", {"path": "notes.txt", "max_lines": 10}))

    assert decision.allowed is True


async def test_denies_missing_required_argument(tmp_path: Path) -> None:
    with make_catalog(tmp_path) as catalog:
        gate = SchemaGate(catalog, "files")
        decision = await gate.decide(Call("read_file", {"max_lines": 10}))

    assert decision.allowed is False
    assert "obrigatório" in decision.reason


async def test_denies_extra_unexpected_argument_to_stop_smuggling(tmp_path: Path) -> None:
    with make_catalog(tmp_path) as catalog:
        gate = SchemaGate(catalog, "files")
        decision = await gate.decide(Call("read_file", {"path": "notes.txt", "leak": "segredo"}))

    assert decision.allowed is False
    assert "inesperado" in decision.reason


@pytest.mark.parametrize("bad_lines", ["10", True, 3.14])
async def test_denies_wrong_argument_types_including_bool_as_int(
    tmp_path: Path, bad_lines: object
) -> None:
    with make_catalog(tmp_path) as catalog:
        gate = SchemaGate(catalog, "files")
        decision = await gate.decide(
            Call("read_file", {"path": "notes.txt", "max_lines": bad_lines})
        )

    assert decision.allowed is False
    assert "tipo inválido" in decision.reason


async def test_denies_unpinned_tool_fail_closed(tmp_path: Path) -> None:
    with make_catalog(tmp_path) as catalog:
        gate = SchemaGate(catalog, "files")
        decision = await gate.decide(Call("unknown_tool", {}))

    assert decision.allowed is False
