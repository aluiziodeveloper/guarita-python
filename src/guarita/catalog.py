"""Catálogo de ferramentas aprovadas, com o pin da impressão digital de cada definição."""

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from mcp.types import Tool

from guarita.fingerprint import canonical, fingerprint

# Cada migração roda uma vez, na ordem; PRAGMA user_version guarda quantas já rodaram.
MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE pins (
        server TEXT NOT NULL,
        tool TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        definition TEXT NOT NULL,
        pinned_at TEXT NOT NULL,
        PRIMARY KEY (server, tool)
    )
    """,
)


class PinCatalog:
    def __init__(self, path: str | Path) -> None:
        self._db = sqlite3.connect(path)
        self._migrate()

    def _migrate(self) -> None:
        (version,) = self._db.execute("PRAGMA user_version").fetchone()
        for number, sql in enumerate(MIGRATIONS[version:], start=version + 1):
            with self._db:
                self._db.execute(sql)
                self._db.execute(f"PRAGMA user_version = {number}")

    @property
    def schema_version(self) -> int:
        (version,) = self._db.execute("PRAGMA user_version").fetchone()
        return int(version)

    def pin(self, server: str, tools: Iterable[Tool]) -> list[str]:
        now = datetime.now(UTC).isoformat()
        rows = [(server, t.name, fingerprint(t), canonical(t), now) for t in tools]
        with self._db:
            self._db.executemany(
                "INSERT OR REPLACE INTO pins VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return [row[1] for row in rows]

    def pinned(self, server: str, tool: str) -> str | None:
        row = self._db.execute(
            "SELECT fingerprint FROM pins WHERE server = ? AND tool = ?",
            (server, tool),
        ).fetchone()
        return None if row is None else str(row[0])

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
