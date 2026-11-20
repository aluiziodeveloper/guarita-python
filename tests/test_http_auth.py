from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from mcp import Client

from guarita.auth import AuthError, JwtVerifier
from guarita.domain import Call, Decision
from guarita.http_server import build_http_app
from guarita.lab.server import build_server

pytestmark = pytest.mark.anyio

SIGNING_KEY = "guarita-lab-signing-key-32-bytes-min"
AUDIENCE = "guarita-mcp"
ISSUER = "guarita-idp"


def issue_jwt(sub: str = "ops-bot", expired: bool = False, aud: str = AUDIENCE) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=1) if expired else now + timedelta(minutes=5)
    return jwt.encode({"sub": sub, "aud": aud, "iss": ISSUER, "exp": exp}, SIGNING_KEY, "HS256")


class CaptureAgentGate:
    def __init__(self) -> None:
        self.seen_agents: list[str] = []

    async def decide(self, call: Call) -> Decision:
        self.seen_agents.append(call.agent)
        return Decision.allow()


def test_jwt_verifier_rejects_expired_or_wrong_audience() -> None:
    verifier = JwtVerifier(SIGNING_KEY, audience=AUDIENCE, issuer=ISSUER)

    assert verifier.verify(issue_jwt("support-bot")).agent_id == "support-bot"
    with pytest.raises(AuthError):
        verifier.verify(issue_jwt("support-bot", expired=True))
    with pytest.raises(AuthError):
        verifier.verify(issue_jwt("support-bot", aud="other-service"))


async def test_http_gateway_enforces_origin_and_jwt_and_binds_agent_identity() -> None:
    verifier = JwtVerifier(SIGNING_KEY, audience=AUDIENCE, issuer=ISSUER)
    gate = CaptureAgentGate()
    async with Client(build_server()) as upstream:
        app = build_http_app(
            upstream,
            verifier=verifier,
            allowed_origins={"https://agent.corp.test"},
            gate=gate,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://guarita.test") as client:
            no_auth = await client.post("/mcp", json={"method": "tools/call", "params": {}})
            bad_origin = await client.post(
                "/mcp",
                headers={
                    "Authorization": f"Bearer {issue_jwt('ops-bot')}",
                    "Origin": "https://evil.test",
                },
                json={"method": "tools/call", "params": {"name": "read_file", "arguments": {}}},
            )
            ok = await client.post(
                "/mcp",
                headers={
                    "Authorization": f"Bearer {issue_jwt('ops-bot')}",
                    "Origin": "https://agent.corp.test",
                },
                json={
                    "method": "tools/call",
                    "params": {"name": "read_file", "arguments": {"path": "notes.txt"}},
                },
            )

    assert no_auth.status_code == 401
    assert bad_origin.status_code == 403
    assert ok.status_code == 200
    assert ok.json()["isError"] is False
    assert gate.seen_agents == ["ops-bot"]
