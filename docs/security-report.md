# Relatório de segurança da Guarita

Gerado por `uv run python -m guarita.report > docs/security-report.md`.

## Resumo executivo

- **Ameaças modeladas:** 11 (11 em estado *parcialmente mitigada*, 0 declaradas resolvidas por completo).
- **Mapeamento OWASP 2026 (cobertura parcial declarada):**
  - **OWASP LLM Top 10 2026:** LLM01:2026, LLM02:2026, LLM03:2026, LLM06:2026
  - **OWASP Agentic Top 10 2026:** ASI01, ASI02, ASI03, ASI04, ASI05, ASI06, ASI08, ASI09
  - **OWASP MCP Top 10:** MCP01, MCP02, MCP03, MCP04, MCP05, MCP06, MCP07, MCP08, MCP10

## Matriz de defesas

| Ameaça | OWASP 2026 | Estado | Defesa implementada |
|---|---|---|---|
| `tool-poisoning` | MCP03, LLM01:2026, ASI01 | parcialmente mitigada | portão (02-03) + varredor NFKC e Unicode invisível (03-05) |
| `rug-pull` | MCP04, ASI04 | parcialmente mitigada | catálogo SQLite com pin SHA-256 canônico (03-01 a 03-03) |
| `tool-shadowing` | MCP03, ASI02 | parcialmente mitigada | namespace por servidor e silhueta anti-homóglifos (03-06) |
| `excessive-agency` | LLM03:2026, ASI02, MCP02 | parcialmente mitigada | política TOML default-deny por agente e argumento (04-01 e 04-02) |
| `approval-fatigue` | ASI09 | parcialmente mitigada | aprovação com prazo, limite de fila e resfriamento (04-03 e 04-04) |
| `data-exfiltration` | LLM02:2026, MCP01, MCP10 | parcialmente mitigada | schema fixado, DLP (CPF, segredos, Base64, entropia) e egress allowlist (05-01 a 05-04) |
| `indirect-prompt-injection` | LLM01:2026, MCP06, ASI01, ASI06 | parcialmente mitigada | revisão de resposta, detector, delimitador aleatório e classificador (06-01 a 06-04) |
| `resource-abuse` | LLM06:2026, ASI08 | parcialmente mitigada | token bucket, orçamento de custo e disjuntor (07-02 e 07-03) |
| `unexpected-execution` | ASI05, MCP05 | parcialmente mitigada | contêiner sem rede, somente leitura e sem capabilities para stdio (07-04) |
| `credential-misuse` | MCP07, ASI03, MCP01 | parcialmente mitigada | identidade por JWT, Origin guard e credencial dedicada por servidor (08-03 e 08-04) |
| `audit-tampering` | MCP08 | parcialmente mitigada | trilha JSONL encadeada por SHA-256 e verificador audit-verify (08-01 e 08-02) |

## Costuras fechadas no red team (módulo 09)

- DLP normaliza Unicode (NFKC e categoria Cf) antes de validar CPF e segredos.
- Política decodifica percent-encoding (%2e%2e) em dois passes antes de checar '..'.
- UntrustedWrapper atualiza content e structured_content (compatível com outputSchema do SDK 2.x).

## Lacunas declaradas

- Paráfrases semânticas sem marcadores nem Unicode invisível podem passar no varredor estático.
- Exfiltração fatiada em várias chamadas (drip exfiltration) ou esteganografia em prosa comum.
- Reescrita total da trilha local por usuário root exige ancoragem externa (WORM/Object Lock).
- Contêineres Docker compartilham o kernel; cargas multi-tenant pedem gVisor ou microVM.
- Aprovação humana reduz superfície mas depende da atenção do operador em cada decisão.
