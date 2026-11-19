import re
from pathlib import Path

from guarita.threats import THREATS, Status, render_markdown

OWASP_ID = re.compile(r"MCP(0[1-9]|10)|ASI(0[1-9]|10)|LLM(0[1-9]|10):2026")
DOC = Path(__file__).parent.parent / "docs" / "threats.md"


def test_threat_ids_are_unique() -> None:
    ids = [t.id for t in THREATS]
    assert len(ids) == len(set(ids))


def test_every_threat_points_to_real_owasp_entries() -> None:
    for threat in THREATS:
        assert threat.owasp, threat.id
        for ref in threat.owasp:
            assert OWASP_ID.fullmatch(ref), f"{threat.id}: {ref}"


def test_a_partial_mitigation_names_its_defense() -> None:
    for threat in THREATS:
        assert (threat.status is Status.PARTIAL) == bool(threat.defense), threat.id


def test_the_document_matches_the_code() -> None:
    assert DOC.read_text(encoding="utf-8") == render_markdown()
