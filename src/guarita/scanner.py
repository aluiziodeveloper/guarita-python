"""Varredor de descrições de ferramentas MCP: da lista ingênua à normalização NFKC."""

import unicodedata
from dataclasses import dataclass

from mcp.types import Tool

from guarita.domain import Decision

SUSPICIOUS_PHRASES: tuple[str, ...] = (
    "<important>",
    "</important>",
    "ignore previous",
    "ignore all previous",
    "ignore as instruções",
    "~/.ssh/id_rsa",
    "não a mencione ao usuário",
    "do not mention",
)


@dataclass(frozen=True)
class Finding:
    rule: str
    detail: str


class NaiveScanner:
    """Defesa ingênua: procura frases fixas em minúsculas na descrição bruta."""

    def __init__(self, phrases: tuple[str, ...] = SUSPICIOUS_PHRASES) -> None:
        self._phrases = phrases

    def scan(self, tool: Tool) -> list[Finding]:
        text = (tool.description or "").lower()
        return [
            Finding("suspicious-phrase", f"frase suspeita: {phrase!r}")
            for phrase in self._phrases
            if phrase in text
        ]


def invisible_chars(text: str) -> list[str]:
    """Lista os pontos de código invisíveis de formatação (categoria Unicode Cf)."""
    return [f"U+{ord(ch):04X}" for ch in text if unicodedata.category(ch) == "Cf"]


def normalize_text(text: str) -> str:
    """Remove caracteres invisíveis (Cf), aplica NFKC e converte para minúsculas."""
    visible = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return unicodedata.normalize("NFKC", visible).casefold()


class DescriptionScanner:
    """Varredor robusto: acusa Unicode invisível e aplica NFKC antes de buscar frases."""

    def __init__(self, phrases: tuple[str, ...] = SUSPICIOUS_PHRASES) -> None:
        self._phrases = tuple(normalize_text(p) for p in phrases)

    def scan(self, tool: Tool) -> list[Finding]:
        raw = tool.description or ""
        findings: list[Finding] = []
        hidden = invisible_chars(raw)
        if hidden:
            findings.append(
                Finding("invisible-unicode", f"caracteres invisíveis: {', '.join(hidden)}")
            )
        normalized = normalize_text(raw)
        for phrase in self._phrases:
            if phrase in normalized:
                findings.append(Finding("suspicious-phrase", f"frase suspeita: {phrase!r}"))
        return findings

    def check(self, tool: Tool) -> Decision:
        findings = self.scan(tool)
        if not findings:
            return Decision.allow()
        summary = "; ".join(f.detail for f in findings)
        return Decision.deny(f"descrição suspeita em {tool.name}: {summary}")
