"""DLP (Data Loss Prevention): detecta segredos e CPFs válidos nos argumentos."""

import re
from collections.abc import Iterator, Mapping
from typing import Any

from guarita.domain import Call, Decision

CPF_PATTERN = re.compile(r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)")

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})\b")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


def is_valid_cpf(raw: str) -> bool:
    """Confere os dois dígitos verificadores do CPF, rejeitando sequências repetidas."""
    digits = [int(ch) for ch in raw if ch.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    first = (sum(d * w for d, w in zip(digits[:9], range(10, 1, -1), strict=True)) * 10) % 11
    dv1 = 0 if first == 10 else first
    second = (sum(d * w for d, w in zip(digits[:10], range(11, 1, -1), strict=True)) * 10) % 11
    dv2 = 0 if second == 10 else second
    return digits[9] == dv1 and digits[10] == dv2


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def scan_text(text: str) -> list[str]:
    """Devolve apenas os tipos encontrados — nunca o segredo ou o CPF em claro."""
    kinds: list[str] = []
    for match in CPF_PATTERN.finditer(text):
        if is_valid_cpf(match.group(1)):
            kinds.append("cpf")
            break
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            kinds.append(kind)
    return kinds


class DlpGate:
    """Inspeciona todos os textos aninhados nos argumentos contra vazamento de dados."""

    async def decide(self, call: Call) -> Decision:
        found: list[str] = []
        for text in _iter_strings(call.arguments):
            for kind in scan_text(text):
                if kind not in found:
                    found.append(kind)
        if not found:
            return Decision.allow()
        return Decision.deny(f"vazamento detectado nos argumentos: {', '.join(found)}")
