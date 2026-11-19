"""Varredor de descrições de ferramentas MCP (versão ingênua: lista de frases)."""

from dataclasses import dataclass

from mcp.types import Tool

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
