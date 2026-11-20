"""Modelo de ameaças como dados: a fonte de docs/threats.md, conferida por teste."""

from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    OPEN = "aberta"
    PARTIAL = "parcialmente mitigada"


@dataclass(frozen=True)
class Threat:
    id: str
    title: str
    owasp: tuple[str, ...]
    module: str
    status: Status = Status.OPEN
    defense: str = ""


THREATS: tuple[Threat, ...] = (
    Threat(
        "tool-poisoning",
        "Ordem escondida na descrição de uma ferramenta",
        ("MCP03", "LLM01:2026", "ASI01"),
        "03",
        Status.PARTIAL,
        "portão (02-03) + varredor NFKC e Unicode invisível (03-05)",
    ),
    Threat(
        "rug-pull",
        "Troca silenciosa da definição aprovada",
        ("MCP04", "ASI04"),
        "03",
        Status.PARTIAL,
        "catálogo SQLite com pin SHA-256 canônico (03-01 a 03-03)",
    ),
    Threat(
        "tool-shadowing",
        "Ferramenta que imita o nome de outra",
        ("MCP03", "ASI02"),
        "03",
        Status.PARTIAL,
        "namespace por servidor e silhueta anti-homóglifos (03-06)",
    ),
    Threat(
        "excessive-agency",
        "Agente com mais permissão do que a tarefa pede",
        ("LLM03:2026", "ASI02", "MCP02"),
        "04",
        Status.PARTIAL,
        "política TOML default-deny por agente e argumento (04-01 e 04-02)",
    ),
    Threat(
        "approval-fatigue",
        "Aprovação humana obtida por cansaço",
        ("ASI09",),
        "04",
        Status.PARTIAL,
        "aprovação com prazo, limite de fila e resfriamento (04-03 e 04-04)",
    ),
    Threat(
        "data-exfiltration",
        "Segredo ou dado pessoal saindo nos argumentos",
        ("LLM02:2026", "MCP01", "MCP10"),
        "05",
        Status.PARTIAL,
        "schema fixado, DLP (CPF, segredos, Base64, entropia) e egress allowlist (05-01 a 05-04)",
    ),
    Threat(
        "indirect-prompt-injection",
        "Instrução escondida no resultado de uma ferramenta",
        ("LLM01:2026", "MCP06", "ASI01", "ASI06"),
        "06",
        Status.PARTIAL,
        "revisão de resposta, detector, delimitador aleatório e classificador (06-01 a 06-04)",
    ),
    Threat(
        "resource-abuse",
        "Laço de chamadas que esgota cota ou custo",
        ("LLM06:2026", "ASI08"),
        "07",
        Status.PARTIAL,
        "token bucket, orçamento de custo e disjuntor (07-02 e 07-03)",
    ),
    Threat(
        "unexpected-execution",
        "Servidor de ferramentas executando no host",
        ("ASI05", "MCP05"),
        "07",
        Status.PARTIAL,
        "contêiner sem rede, somente leitura e sem capabilities para stdio (07-04)",
    ),
    Threat(
        "credential-misuse",
        "Token do usuário repassado ao servidor (confused deputy)",
        ("MCP07", "ASI03", "MCP01"),
        "08",
        Status.PARTIAL,
        "identidade por JWT, Origin guard e credencial dedicada por servidor (08-03 e 08-04)",
    ),
    Threat(
        "audit-tampering",
        "Registro apagado, editado ou ausente",
        ("MCP08",),
        "08",
        Status.PARTIAL,
        "trilha JSONL encadeada por SHA-256 e verificador audit-verify (08-01 e 08-02)",
    ),
)


def render_markdown(threats: tuple[Threat, ...] = THREATS) -> str:
    lines = [
        "# Modelo de ameaças",
        "",
        "Gerado por `uv run python -m guarita.threats > docs/threats.md`.",
        "",
        "| Ameaça | Descrição | OWASP | Módulo | Estado | Defesa |",
        "|---|---|---|---|---|---|",
    ]
    for t in threats:
        refs = ", ".join(t.owasp)
        lines.append(
            f"| `{t.id}` | {t.title} | {refs} | {t.module} | {t.status} | {t.defense or '-'} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_markdown(), end="")
