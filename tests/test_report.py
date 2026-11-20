from pathlib import Path

from guarita.report import DECLARED_GAPS, render_security_report

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_security_report_covers_all_three_owasp_2026_lists_with_honest_gaps() -> None:
    report = render_security_report()

    assert "LLM Top 10 2026" in report
    assert "Agentic Top 10 2026" in report
    assert "MCP Top 10" in report
    assert "cobertura parcial" in report.lower()
    assert "100% seguro" not in report.lower()
    assert len(DECLARED_GAPS) >= 4
    for gap in DECLARED_GAPS:
        assert gap in report


def test_docs_security_report_matches_code() -> None:
    expected = render_security_report()
    actual = (REPO_ROOT / "docs/security-report.md").read_text(encoding="utf-8")

    assert actual == expected
