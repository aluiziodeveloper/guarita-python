from pathlib import Path

import pytest

from guarita.audit import GENESIS_HASH, AuditingGate, AuditTrail
from guarita.domain import Call
from guarita.gate import ArgumentAllowlist

pytestmark = pytest.mark.anyio


async def test_records_chained_decisions_without_storing_raw_secrets(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    trail = AuditTrail(log_path)
    gate = AuditingGate(ArgumentAllowlist("read_file", "path", ["notes.txt"]), trail)

    sensitive_arg = "CPF-529.982.247-25-DADO"
    await gate.decide(Call("read_file", {"path": "notes.txt"}, agent="ops-bot"))
    await gate.decide(Call("read_file", {"path": sensitive_arg}, agent="ops-bot"))

    entries = trail.entries()
    assert len(entries) == 2
    assert entries[0].seq == 1
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[0].verdict == "allow"
    assert entries[1].seq == 2
    assert entries[1].prev_hash == entries[0].entry_hash
    assert entries[1].verdict == "deny"

    raw_file = log_path.read_text(encoding="utf-8")
    assert sensitive_arg not in raw_file
    assert "529.982.247-25" not in raw_file
