"""Porta de revisão das respostas das ferramentas na volta para o agente."""

from typing import Protocol

from mcp.types import CallToolResult, TextContent

from guarita.domain import Call


class ResultReviewer(Protocol):
    """Inspeciona ou transforma a resposta de uma ferramenta antes de devolvê-la ao agente."""

    async def review(self, call: Call, result: CallToolResult) -> CallToolResult: ...


def extract_text(result: CallToolResult) -> str:
    return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def replace_text(result: CallToolResult, new_text: str) -> CallToolResult:
    structured = result.structured_content
    if isinstance(structured, dict) and "result" in structured:
        structured = {**structured, "result": new_text}
    return CallToolResult(
        content=[TextContent(type="text", text=new_text)],
        structured_content=structured,
        is_error=result.is_error,
    )
