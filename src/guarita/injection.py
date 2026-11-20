"""Detector determinístico de injeção indireta na resposta da ferramenta."""

import re

from mcp.types import CallToolResult

from guarita.domain import Call
from guarita.proxy import refusal
from guarita.response import extract_text
from guarita.scanner import invisible_chars, normalize_text

INJECTION_MARKERS: tuple[str, ...] = (
    "<|im_start|>",
    "<|system|>",
    "<important>",
    "ignore previous instructions",
    "ignore all previous",
    "ignore as instruções anteriores",
    "disregard previous",
    "system prompt:",
)

HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def detect_injection(text: str) -> list[str]:
    reasons: list[str] = []
    hidden = invisible_chars(text)
    if hidden:
        reasons.append(f"caracteres invisíveis ({', '.join(hidden)})")
    normalized = normalize_text(text)
    for marker in INJECTION_MARKERS:
        if marker in normalized:
            reasons.append(f"marcador de injeção ({marker!r})")
    for comment in HTML_COMMENT.findall(normalized):
        if any(word in comment for word in ("ignore", "chame", "envie", "leia", "system")):
            reasons.append("instrução oculta em comentário HTML")
            break
    return reasons


class InjectionReviewer:
    """Bloqueia respostas com marcadores de troca de papel ou texto oculto."""

    async def review(self, call: Call, result: CallToolResult) -> CallToolResult:
        if result.is_error:
            return result
        reasons = detect_injection(extract_text(result))
        if reasons:
            return refusal(f"injeção indireta em {call.tool}: {'; '.join(reasons)}")
        return result
