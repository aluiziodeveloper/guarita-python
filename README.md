# Guarita (Python)

Firewall para agentes de IA que usam o Model Context Protocol (MCP), construído aula a aula no curso
*Segurança de Agentes de IA e MCP com Python*.

## Como rodar

Requer o [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.14 e as dependências:

```bash
uv sync
uv run guarita --version
```

## Verificações

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
