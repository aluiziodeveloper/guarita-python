# Modelo de ameaças

Gerado por `uv run python -m guarita.threats > docs/threats.md`.

| Ameaça | Descrição | OWASP | Módulo | Estado | Defesa |
|---|---|---|---|---|---|
| `tool-poisoning` | Ordem escondida na descrição de uma ferramenta | MCP03, LLM01:2026, ASI01 | 03 | parcialmente mitigada | portão (02-03) + varredor NFKC e Unicode invisível (03-05) |
| `rug-pull` | Troca silenciosa da definição aprovada | MCP04, ASI04 | 03 | parcialmente mitigada | catálogo SQLite com pin SHA-256 canônico (03-01 a 03-03) |
| `tool-shadowing` | Ferramenta que imita o nome de outra | MCP03, ASI02 | 03 | parcialmente mitigada | namespace por servidor e silhueta anti-homóglifos (03-06) |
| `excessive-agency` | Agente com mais permissão do que a tarefa pede | LLM03:2026, ASI02, MCP02 | 04 | parcialmente mitigada | política TOML default-deny por agente e argumento (04-01 e 04-02) |
| `approval-fatigue` | Aprovação humana obtida por cansaço | ASI09 | 04 | parcialmente mitigada | aprovação com prazo, limite de fila e resfriamento (04-03 e 04-04) |
| `data-exfiltration` | Segredo ou dado pessoal saindo nos argumentos | LLM02:2026, MCP01, MCP10 | 05 | parcialmente mitigada | schema fixado, DLP (CPF, segredos, Base64, entropia) e egress allowlist (05-01 a 05-04) |
| `indirect-prompt-injection` | Instrução escondida no resultado de uma ferramenta | LLM01:2026, MCP06, ASI01, ASI06 | 06 | parcialmente mitigada | revisão de resposta, detector, delimitador aleatório e classificador (06-01 a 06-04) |
| `resource-abuse` | Laço de chamadas que esgota cota ou custo | LLM06:2026, ASI08 | 07 | parcialmente mitigada | token bucket, orçamento de custo e disjuntor (07-02 e 07-03) |
| `unexpected-execution` | Servidor de ferramentas executando no host | ASI05, MCP05 | 07 | parcialmente mitigada | contêiner sem rede, somente leitura e sem capabilities para stdio (07-04) |
| `credential-misuse` | Token do usuário repassado ao servidor (confused deputy) | MCP07, ASI03, MCP01 | 08 | parcialmente mitigada | identidade por JWT, Origin guard e credencial dedicada por servidor (08-03 e 08-04) |
| `audit-tampering` | Registro apagado, editado ou ausente | MCP08 | 08 | parcialmente mitigada | trilha JSONL encadeada por SHA-256 e verificador audit-verify (08-01 e 08-02) |
