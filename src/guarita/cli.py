"""Linha de comando da Guarita."""

import argparse
import asyncio
from collections.abc import Sequence

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server.stdio import stdio_server

from guarita import __version__
from guarita.gate import AllOf, ArgumentAllowlist, Gate
from guarita.proxy import build_proxy


def parse_allow(spec: str) -> ArgumentAllowlist:
    """Lê "ferramenta:argumento=valor1,valor2" (ex.: "read_file:path=notes.txt")."""
    tool, sep, rest = spec.partition(":")
    argument, eq, values = rest.partition("=")
    if not (sep and eq and tool and argument and values):
        raise argparse.ArgumentTypeError(f"use ferramenta:argumento=valor[,valor]: {spec!r}")
    return ArgumentAllowlist(tool, argument, values.split(","))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guarita",
        description="Firewall para agentes de IA que usam MCP.",
    )
    parser.add_argument("--version", action="version", version=f"guarita {__version__}")
    commands = parser.add_subparsers(dest="command")
    stdio = commands.add_parser("stdio", help="atende o agente por stdio na frente de um servidor")
    stdio.add_argument("--allow", type=parse_allow, action="append", default=[])
    stdio.add_argument("upstream", nargs="+", help="comando do servidor MCP, depois de --")
    return parser


async def serve_stdio(upstream_command: list[str], gate: Gate) -> None:
    params = StdioServerParameters(command=upstream_command[0], args=upstream_command[1:])
    async with Client(params) as upstream:
        server = build_proxy(upstream, gate)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stdio":
        asyncio.run(serve_stdio(args.upstream, AllOf(args.allow)))
    return 0
