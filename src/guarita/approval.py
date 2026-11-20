"""Aprovação humana com prazo, limite de fila e resfriamento contra fadiga."""

import asyncio
import html
import json
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from guarita.domain import Call, Decision, Verdict
from guarita.gate import Gate


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    id: str
    call: Call
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    note: str = ""
    _done: asyncio.Event = field(default_factory=asyncio.Event, repr=False, compare=False)


class ApprovalBroker:
    """Gerencia aprovações pendentes com falha fechada, limite por agente e resfriamento."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_pending_per_agent: int = 3,
        cooldown_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_pending = max_pending_per_agent
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._requests: dict[str, ApprovalRequest] = {}
        self._cooldown_until: dict[tuple[str, str], float] = {}

    def create_pending(self, call: Call, reason: str) -> ApprovalRequest:
        req = ApprovalRequest(id=secrets.token_hex(6), call=call, reason=reason)
        self._requests[req.id] = req
        return req

    def pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status is ApprovalStatus.PENDING]

    def history(self) -> list[ApprovalRequest]:
        return list(self._requests.values())

    def approve(self, request_id: str) -> None:
        req = self._requests[request_id]
        if req.status is ApprovalStatus.PENDING:
            req.status = ApprovalStatus.APPROVED
            req._done.set()

    def deny(self, request_id: str, note: str = "negado pelo operador") -> None:
        req = self._requests[request_id]
        if req.status is ApprovalStatus.PENDING:
            req.status = ApprovalStatus.DENIED
            req.note = note
            key = (req.call.agent, req.call.tool)
            self._cooldown_until[key] = self._clock() + self._cooldown
            req._done.set()

    async def wait_for_decision(self, call: Call, reason: str) -> Decision:
        key = (call.agent, call.tool)
        if self._clock() < self._cooldown_until.get(key, 0.0):
            return Decision.deny(f"em resfriamento após recusa anterior para {call.tool}")
        agent_pending = sum(1 for r in self.pending() if r.call.agent == call.agent)
        if agent_pending >= self._max_pending:
            return Decision.deny(f"limite de pendências atingido para {call.agent}")
        req = self.create_pending(call, reason)
        try:
            await asyncio.wait_for(req._done.wait(), timeout=self._timeout)
        except TimeoutError:
            if req.status is ApprovalStatus.PENDING:
                req.status = ApprovalStatus.EXPIRED
            return Decision.deny(f"aprovação expirada para {call.tool}")
        if req.status is ApprovalStatus.APPROVED:
            return Decision.allow()
        return Decision.deny(req.note or f"aprovação negada para {call.tool}")


class ApprovalGate:
    """Envolve um portão de política: só pausa no broker quando o veredito é ASK."""

    def __init__(self, inner: Gate, broker: ApprovalBroker) -> None:
        self._inner = inner
        self._broker = broker

    async def decide(self, call: Call) -> Decision:
        decision = await self._inner.decide(call)
        if decision.verdict is not Verdict.ASK:
            return decision
        return await self._broker.wait_for_decision(call, decision.reason)


def render_approval_html(requests: list[ApprovalRequest]) -> str:
    """Gera uma página local simples para o operador revisar pedidos sem risco de XSS."""
    rows = []
    for req in requests:
        args = html.escape(json.dumps(dict(req.call.arguments), ensure_ascii=False))
        rows.append(
            f"<article class='card'>"
            f"<h2>{html.escape(req.call.tool)} <small>({html.escape(req.call.agent)})</small></h2>"
            f"<p><strong>Motivo:</strong> {html.escape(req.reason)}</p>"
            f"<pre><code>{args}</code></pre>"
            f"<p class='meta'>ID: {html.escape(req.id)} · Estado: {html.escape(req.status)}</p>"
            f"</article>"
        )
    body = "\n".join(rows) or "<p>Nenhum pedido pendente.</p>"
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<title>Guarita · Aprovação humana</title>"
        "<style>body{background:#0f1420;color:#e8ecf4;font-family:Inter,sans-serif;padding:32px}"
        ".card{background:#182033;border:1px solid #212b42;border-radius:14px;padding:20px;"
        "margin-bottom:16px}h1{color:#e0234e}h2{color:#4cc3ff;margin:0 0 8px}"
        "pre{background:#0b0f19;padding:12px;border-radius:8px;overflow:auto}</style></head>"
        f"<body><h1>Guarita · Fila de aprovação</h1>{body}</body></html>"
    )
