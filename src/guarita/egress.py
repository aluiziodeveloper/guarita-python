"""Controle de destinos (egress): só permite URLs HTTPS para hosts aprovados."""

import ipaddress
import re
from collections.abc import Iterable, Iterator, Mapping
from typing import Any
from urllib.parse import urlsplit

from guarita.domain import Call, Decision

URL_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"'<>]+")


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


def check_url(raw_url: str, allowed_hosts: frozenset[str]) -> Decision:
    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() != "https":
        return Decision.deny(f"esquema não permitido em URL: {parsed.scheme}")
    if parsed.username is not None or parsed.password is not None:
        return Decision.deny("URL com userinfo é recusada")
    host = (parsed.hostname or "").lower()
    if not host:
        return Decision.deny("URL sem host")
    if _is_ip_literal(host):
        return Decision.deny("URL com IP literal é recusada")
    if host not in allowed_hosts:
        return Decision.deny(f"destino fora da lista permitida: {host}")
    return Decision.allow()


class EgressGate:
    """Inspeciona URLs em qualquer argumento e libera apenas hosts HTTPS aprovados."""

    def __init__(self, allowed_hosts: Iterable[str]) -> None:
        self._allowed = frozenset(h.lower() for h in allowed_hosts)

    async def decide(self, call: Call) -> Decision:
        for text in _iter_strings(call.arguments):
            for url in URL_PATTERN.findall(text):
                decision = check_url(url, self._allowed)
                if not decision.allowed:
                    return decision
        return Decision.allow()
