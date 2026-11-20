"""DLP (Data Loss Prevention): segredos, CPFs, Base64 e alta entropia nos argumentos."""

import base64
import binascii
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator, Mapping
from typing import Any

from guarita.domain import Call, Decision

CPF_PATTERN = re.compile(r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)")
BASE64_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/=_-])([A-Za-z0-9+/_-]{12,}={0,2})(?![A-Za-z0-9+/=_-])"
)
TOKEN_CANDIDATE = re.compile(r"[A-Za-z0-9+/_-]{24,}")

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


def shannon_entropy(token: str) -> float:
    """Entropia de Shannon em bits por caractere."""
    if not token:
        return 0.0
    counts = Counter(token)
    total = len(token)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def _decode_base64(candidate: str) -> str | None:
    padded = candidate + "=" * (-len(candidate) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        decoded = raw.decode("utf-8")
    except binascii.Error, UnicodeDecodeError, ValueError:
        return None
    if not decoded or any(ord(ch) < 32 and ch not in "\t\n\r" for ch in decoded):
        return None
    return decoded


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def _has_mixed_classes(token: str) -> bool:
    has_upper = any(ch.isupper() for ch in token)
    has_lower = any(ch.islower() for ch in token)
    has_digit = any(ch.isdigit() for ch in token)
    return has_upper and has_lower and has_digit


def _normalize_for_dlp(text: str) -> str:
    visible = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return unicodedata.normalize("NFKC", visible)


def scan_text(text: str, depth: int = 2, entropy_threshold: float = 4.3) -> list[str]:
    """Devolve apenas os tipos encontrados — nunca o segredo ou o CPF em claro."""
    text = _normalize_for_dlp(text)
    kinds: list[str] = []
    for match in CPF_PATTERN.finditer(text):
        if is_valid_cpf(match.group(1)):
            kinds.append("cpf")
            break
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            kinds.append(kind)
    if depth > 0:
        for b64 in BASE64_CANDIDATE.findall(text):
            decoded = _decode_base64(b64)
            if decoded and decoded != text:
                for nested in scan_text(
                    decoded, depth=depth - 1, entropy_threshold=entropy_threshold
                ):
                    if nested not in kinds:
                        kinds.append(nested)
    if not kinds:
        for token in TOKEN_CANDIDATE.findall(text):
            if _has_mixed_classes(token) and shannon_entropy(token) >= entropy_threshold:
                kinds.append("high-entropy")
                break
    return kinds


class DlpGate:
    """Inspeciona todos os textos aninhados nos argumentos contra vazamento de dados."""

    def __init__(self, entropy_threshold: float = 4.3) -> None:
        self._entropy_threshold = entropy_threshold

    async def decide(self, call: Call) -> Decision:
        found: list[str] = []
        for text in _iter_strings(call.arguments):
            for kind in scan_text(text, entropy_threshold=self._entropy_threshold):
                if kind not in found:
                    found.append(kind)
        if not found:
            return Decision.allow()
        return Decision.deny(f"vazamento detectado nos argumentos: {', '.join(found)}")
