"""Servidor MCP do laboratório.

Nenhuma ferramenta daqui toca o disco: os "arquivos" são marcadores sintéticos em memória.
"""

import argparse
from collections.abc import Sequence

from mcp.server.mcpserver import MCPServer

FILES: dict[str, str] = {
    "notes.txt": "Reunião de planejamento na quinta, às 15h. Levar o relatório de custos.",
    "~/.ssh/id_rsa": "LAB-ONLY-SYNTHETIC-SSH-KEY-DO-NOT-USE",
}

READ_FILE_DESCRIPTION = "Lê um arquivo de texto do projeto e devolve o conteúdo."


def build_server() -> MCPServer:
    server = MCPServer("lab-files")

    @server.tool(description=READ_FILE_DESCRIPTION)
    def read_file(path: str) -> str:
        if path not in FILES:
            raise ValueError(f"arquivo não encontrado no laboratório: {path}")
        return FILES[path]

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guarita-lab-server")
    parser.parse_args(argv)
    build_server().run("stdio")
    return 0
