import sqlite3
from pathlib import Path

from mcp.types import Tool

from guarita.catalog import MIGRATIONS, PinCatalog
from guarita.fingerprint import fingerprint

SCHEMA = {"type": "object", "properties": {"path": {"type": "string"}}}


def tool(name: str, description: str = "Lê um arquivo.") -> Tool:
    return Tool(name=name, description=description, input_schema=SCHEMA)


def test_a_new_catalog_runs_every_migration(tmp_path: Path) -> None:
    with PinCatalog(tmp_path / "catalog.db") as catalog:
        assert catalog.schema_version == len(MIGRATIONS)


def test_reopening_does_not_run_migrations_again(tmp_path: Path) -> None:
    path = tmp_path / "catalog.db"
    with PinCatalog(path) as catalog:
        catalog.pin("files", [tool("read_file")])
    with PinCatalog(path) as catalog:
        assert catalog.pinned("files", "read_file") == fingerprint(tool("read_file"))


def test_pins_each_tool_under_its_server(tmp_path: Path) -> None:
    with PinCatalog(tmp_path / "catalog.db") as catalog:
        names = catalog.pin("files", [tool("read_file"), tool("list_dir")])

        assert names == ["read_file", "list_dir"]
        assert catalog.pinned("files", "list_dir") == fingerprint(tool("list_dir"))
        assert catalog.pinned("mail", "read_file") is None


def test_pinning_again_replaces_the_fingerprint(tmp_path: Path) -> None:
    with PinCatalog(tmp_path / "catalog.db") as catalog:
        catalog.pin("files", [tool("read_file")])
        catalog.pin("files", [tool("read_file", "Lê um arquivo de texto.")])

        assert catalog.pinned("files", "read_file") == fingerprint(
            tool("read_file", "Lê um arquivo de texto.")
        )


def test_stores_the_canonical_definition_for_review(tmp_path: Path) -> None:
    path = tmp_path / "catalog.db"
    with PinCatalog(path) as catalog:
        catalog.pin("files", [tool("read_file")])

    db = sqlite3.connect(path)
    (definition,) = db.execute("SELECT definition FROM pins").fetchone()
    db.close()
    assert '"description":"Lê um arquivo."' in definition
