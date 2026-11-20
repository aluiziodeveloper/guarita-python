import asyncio

import pytest

from guarita.approval import ApprovalBroker, ApprovalGate, ApprovalStatus, render_approval_html
from guarita.domain import Call
from guarita.policy import PolicyGate

pytestmark = pytest.mark.anyio


def ask_policy() -> PolicyGate:
    return PolicyGate.from_toml(
        """
        [[rules]]
        effect = "ask"
        tools = ["send_email"]
        reason = "envio externo exige operador"
        """
    )


async def test_pauses_until_operator_approves() -> None:
    broker = ApprovalBroker(timeout_seconds=2.0)
    gate = ApprovalGate(ask_policy(), broker)

    async def approve_soon() -> None:
        while not broker.pending():
            await asyncio.sleep(0.01)
        broker.approve(broker.pending()[0].id)

    task = asyncio.create_task(approve_soon())
    decision = await gate.decide(Call("send_email", {"to": "dev@corp.test"}, agent="ops-bot"))
    await task

    assert decision.allowed is True


async def test_denies_when_operator_rejects() -> None:
    broker = ApprovalBroker(timeout_seconds=2.0)
    gate = ApprovalGate(ask_policy(), broker)

    async def deny_soon() -> None:
        while not broker.pending():
            await asyncio.sleep(0.01)
        broker.deny(broker.pending()[0].id, "destinatário externo não aprovado")

    task = asyncio.create_task(deny_soon())
    decision = await gate.decide(Call("send_email", {"to": "evil@ext.test"}, agent="ops-bot"))
    await task

    assert decision.allowed is False
    assert "não aprovado" in decision.reason


async def test_expires_and_denies_when_nobody_answers() -> None:
    broker = ApprovalBroker(timeout_seconds=0.05)
    gate = ApprovalGate(ask_policy(), broker)

    decision = await gate.decide(Call("send_email", {"to": "dev@corp.test"}, agent="ops-bot"))

    assert decision.allowed is False
    assert "expirada" in decision.reason
    assert broker.history()[0].status is ApprovalStatus.EXPIRED


def test_approval_html_escapes_untrusted_arguments() -> None:
    broker = ApprovalBroker(timeout_seconds=1.0)
    req = broker.create_pending(
        Call("send_email", {"body": "<script>alert(1)</script>"}, agent="ops-bot"),
        "envio externo",
    )
    page = render_approval_html([req])

    assert "<script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
