from pathlib import Path

import pytest

from guarita.audit import GENESIS_HASH, AuditingGate, AuditTrail, verify_trail
from guarita.cli import main
from guarita.domain import Call, Decision
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


def test_verify_trail_accepts_intact_log_and_detects_edit_or_deletion(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    trail = AuditTrail(log_path)
    trail.record(Call("read_file", {"path": "a.txt"}), Decision.allow())
    trail.record(Call("read_file", {"path": "b.txt"}), Decision.deny("proibido"))
    trail.record(Call("read_file", {"path": "c.txt"}), Decision.allow())

    ok = verify_trail(log_path)
    assert ok.ok is True and ok.entries == 3
    assert main(["audit-verify", str(log_path)]) == 0

    lines = log_path.read_text(encoding="utf-8").splitlines()
    edited = tmp_path / "edited.jsonl"
    edited.write_text("\n".join([lines[0], lines[1].replace("deny", "allow"), lines[2]]) + "\n")
    bad_edit = verify_trail(edited)
    assert bad_edit.ok is False and "linha 2" in bad_edit.error
    assert main(["audit-verify", str(edited)]) == 1

    deleted = tmp_path / "deleted.jsonl"
    deleted.write_text("\n".join([lines[0], lines[2]]) + "\n")
    bad_del = verify_trail(deleted)
    assert bad_del.ok is False and "linha 2" in bad_del.error
