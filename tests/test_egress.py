import pytest

from guarita.domain import Call
from guarita.egress import EgressGate

pytestmark = pytest.mark.anyio


async def test_allows_urls_pointing_to_listed_https_hosts() -> None:
    gate = EgressGate({"api.corp.test", "docs.python.org"})

    decision = await gate.decide(
        Call("fetch", {"url": "https://api.corp.test/v1/status", "note": "sem url"})
    )

    assert decision.allowed is True


@pytest.mark.parametrize(
    ("bad_url", "expected_hint"),
    [
        ("https://evil.test/exfil?d=123", "fora da lista"),
        ("http://api.corp.test/v1/status", "esquema"),
        ("https://api.corp.test@evil.test/steal", "userinfo"),
        ("https://169.254.169.254/latest/meta-data/", "IP literal"),
        ("https://127.0.0.1/admin", "IP literal"),
    ],
)
async def test_blocks_unlisted_hosts_userinfo_tricks_and_ip_literals(
    bad_url: str, expected_hint: str
) -> None:
    gate = EgressGate({"api.corp.test"})

    decision = await gate.decide(Call("fetch", {"payload": f"veja {bad_url}"}))

    assert decision.allowed is False
    assert expected_hint in decision.reason
