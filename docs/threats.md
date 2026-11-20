# Modelo de ameaças

Gerado por `uv run python -m guarita.threats > docs/threats.md`.

| Ameaça | Descrição | OWASP | Módulo | Estado | Defesa |
|---|---|---|---|---|---|
| `tool-poisoning` | Ordem escondida na descrição de uma ferramenta | MCP03, LLM01:2026, ASI01 | 03 | parcialmente mitigada | portão (02-03) + varredor NFKC e Unicode invisível (03-05) |
| `rug-pull` | Troca silenciosa da definição aprovada | MCP04, ASI04 | 03 | parcialmente mitigada | catálogo SQLite com pin SHA-256 canônico (03-01 a 03-03) |
| `tool-shadowing` | Ferramenta que imita o nome de outra | MCP03, ASI02 | 03 | aberta | - |
| `excessive-agency` | Agente com mais permissão do que a tarefa pede | LLM03:2026, ASI02, MCP02 | 04 | aberta | - |
| `approval-fatigue` | Aprovação humana obtida por cansaço | ASI09 | 04 | aberta | - |
| `data-exfiltration` | Segredo ou dado pessoal saindo nos argumentos | LLM02:2026, MCP01, MCP10 | 05 | aberta | - |
| `indirect-prompt-injection` | Instrução escondida no resultado de uma ferramenta | LLM01:2026, MCP06, ASI01, ASI06 | 06 | aberta | - |
| `resource-abuse` | Laço de chamadas que esgota cota ou custo | LLM06:2026, ASI08 | 07 | aberta | - |
| `unexpected-execution` | Servidor de ferramentas executando no host | ASI05, MCP05 | 07 | aberta | - |
| `credential-misuse` | Token do usuário repassado ao servidor (confused deputy) | MCP07, ASI03, MCP01 | 08 | aberta | - |
| `audit-tampering` | Registro apagado, editado ou ausente | MCP08 | 08 | aberta | - |
