# Guarita (Python)

Firewall determinístico para agentes de IA que usam o **Model Context Protocol (MCP)**, construído passo a passo no curso *Segurança de Agentes de IA e MCP com Python*.

Para o agente, a Guarita é um servidor MCP; para os servidores de ferramentas, um cliente MCP. Cada chamada passa por quatro verbos: **decidir**, **inspecionar**, **conter** e **registrar**.

## Como rodar

Requer [`uv`](https://docs.astral.sh/uv/) (que instala o Python 3.14 e trava as dependências via `uv.lock`):

```bash
uv sync
uv run guarita --version
```

### Proxy por stdio com catálogo e lista de argumentos

```bash
uv run guarita pin --catalog catalog.db --server files -- guarita-lab-server --variant honest
uv run guarita stdio --catalog catalog.db --server files --allow read_file:path=notes.txt -- guarita-lab-server --variant poisoned
```

### Verificar integridade da trilha de auditoria

```bash
uv run guarita audit-verify audit.jsonl
```

### Laboratório local (Ollama opcional)

Todo ataque do laboratório roda localmente contra marcadores sintéticos em memória (`LAB-ONLY-SYNTHETIC-...`):

```bash
uv run guarita-lab-measure --runs 20
uv run guarita-lab-eval-classifier
```

## Verificações (mesmas da CI)

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```

## Documentação e arquitetura

- Modelo de ameaças (OWASP 2026): [`docs/threats.md`](docs/threats.md)
- Relatório final de segurança: [`docs/security-report.md`](docs/security-report.md)
- Decisões de arquitetura (ADRs): [`docs/adr/`](docs/adr/)
