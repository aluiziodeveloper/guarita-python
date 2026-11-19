# Guarita (Python)

Firewall para agentes de IA que usam o Model Context Protocol (MCP), construído aula a aula no curso
*Segurança de Agentes de IA e MCP com Python*.

## Como rodar

Requer o [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.14 e as dependências:

```bash
uv sync
uv run guarita --version
```

## A Guarita na frente de um servidor

```bash
uv run guarita stdio --allow read_file:path=notes.txt -- guarita-lab-server --variant poisoned
```

O agente fala com a Guarita por stdio. Ela inicia o servidor depois do `--` e só repassa as
chamadas que o portão deixa passar.

## Verificações

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
