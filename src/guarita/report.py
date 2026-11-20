"""Relatório final de segurança gerado do modelo de ameaças, com cobertura parcial OWASP 2026."""

from guarita.threats import THREATS, Status, Threat

CLOSED_SEAMS: tuple[str, ...] = (
    "DLP normaliza Unicode (NFKC e categoria Cf) antes de validar CPF e segredos.",
    "Política decodifica percent-encoding (%2e%2e) em dois passes antes de checar '..'.",
    (
        "UntrustedWrapper atualiza content e structured_content "
        "(compatível com outputSchema do SDK 2.x)."
    ),
)

DECLARED_GAPS: tuple[str, ...] = (
    "Paráfrases semânticas sem marcadores nem Unicode invisível podem passar no varredor estático.",
    "Exfiltração fatiada em várias chamadas (drip exfiltration) ou esteganografia em prosa comum.",
    "Reescrita total da trilha local por usuário root exige ancoragem externa (WORM/Object Lock).",
    "Contêineres Docker compartilham o kernel; cargas multi-tenant pedem gVisor ou microVM.",
    "Aprovação humana reduz superfície mas depende da atenção do operador em cada decisão.",
)


def _group_by_list(threats: tuple[Threat, ...], prefix: str) -> list[str]:
    found: set[str] = set()
    for t in threats:
        for ref in t.owasp:
            if ref.startswith(prefix):
                found.add(ref)
    return sorted(found)


def render_security_report(threats: tuple[Threat, ...] = THREATS) -> str:
    partial = sum(1 for t in threats if t.status is Status.PARTIAL)
    llm_ids = ", ".join(_group_by_list(threats, "LLM"))
    asi_ids = ", ".join(_group_by_list(threats, "ASI"))
    mcp_ids = ", ".join(_group_by_list(threats, "MCP"))
    summary = (
        f"- **Ameaças modeladas:** {len(threats)} "
        f"({partial} em estado *parcialmente mitigada*, 0 declaradas resolvidas por completo)."
    )
    lines = [
        "# Relatório de segurança da Guarita",
        "",
        "Gerado por `uv run python -m guarita.report > docs/security-report.md`.",
        "",
        "## Resumo executivo",
        "",
        summary,
        "- **Mapeamento OWASP 2026 (cobertura parcial declarada):**",
        f"  - **OWASP LLM Top 10 2026:** {llm_ids}",
        f"  - **OWASP Agentic Top 10 2026:** {asi_ids}",
        f"  - **OWASP MCP Top 10:** {mcp_ids}",
        "",
        "## Matriz de defesas",
        "",
        "| Ameaça | OWASP 2026 | Estado | Defesa implementada |",
        "|---|---|---|---|",
    ]
    for t in threats:
        lines.append(f"| `{t.id}` | {', '.join(t.owasp)} | {t.status} | {t.defense} |")
    lines.extend(["", "## Costuras fechadas no red team (módulo 09)", ""])
    lines.extend(f"- {item}" for item in CLOSED_SEAMS)
    lines.extend(["", "## Lacunas declaradas", ""])
    lines.extend(f"- {gap}" for gap in DECLARED_GAPS)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_security_report(), end="")
