"""Gateway Streamable HTTP mínimo (ASGI) com guarda de Origin e identidade por JWT."""

import json
from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from typing import Any

from guarita.auth import AuthError, JwtVerifier, OriginGuard
from guarita.domain import Call, InvalidCallError
from guarita.gate import AllowAll, Gate
from guarita.proxy import Upstream, refusal
from guarita.response import ResultReviewer

type Scope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
type Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
type AsgiApp = Callable[[Scope, Receive, Send], Awaitable[None]]


async def _send_json(send: Send, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        event = await receive()
        chunks.append(bytes(event.get("body", b"")))
        if not event.get("more_body", False):
            return b"".join(chunks)


def _header(scope: Scope, name: bytes) -> str | None:
    target = name.lower()
    for k, v in scope.get("headers", []):
        if bytes(k).lower() == target:
            return bytes(v).decode("latin-1")
    return None


def build_http_app(
    upstream: Upstream,
    verifier: JwtVerifier,
    allowed_origins: Iterable[str],
    gate: Gate | None = None,
    reviewer: ResultReviewer | None = None,
) -> AsgiApp:
    origin_guard = OriginGuard(allowed_origins)
    active_gate = gate or AllowAll()

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/mcp" or scope.get("method") != "POST":
            await _send_json(send, 404, {"error": "rota não encontrada"})
            return
        if not origin_guard.allows(_header(scope, b"origin")):
            await _send_json(send, 403, {"error": "Origin não permitido"})
            return
        auth = _header(scope, b"authorization") or ""
        if not auth.startswith("Bearer "):
            await _send_json(send, 401, {"error": "Bearer JWT obrigatório"})
            return
        try:
            identity = verifier.verify(auth.removeprefix("Bearer ").strip())
        except AuthError as error:
            await _send_json(send, 401, {"error": str(error)})
            return

        payload = json.loads((await _read_body(receive)).decode("utf-8"))
        method = payload.get("method")
        if method == "tools/list":
            listing = await upstream.list_tools()
            await _send_json(send, 200, listing.model_dump(mode="json", by_alias=True))
            return
        if method != "tools/call":
            await _send_json(send, 400, {"error": f"método não suportado: {method}"})
            return

        params = payload.get("params") or {}
        try:
            call = Call(
                params.get("name", ""), params.get("arguments") or {}, agent=identity.agent_id
            )
        except InvalidCallError as error:
            res = refusal(str(error))
            await _send_json(send, 200, res.model_dump(mode="json", by_alias=True))
            return

        decision = await active_gate.decide(call)
        if not decision.allowed:
            res = refusal(decision.reason)
            await _send_json(send, 200, res.model_dump(mode="json", by_alias=True))
            return

        res = await upstream.call_tool(call.tool, dict(call.arguments))
        if reviewer is not None:
            res = await reviewer.review(call, res)
        await _send_json(send, 200, res.model_dump(mode="json", by_alias=True))

    return app
