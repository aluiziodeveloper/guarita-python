"""Linha de comando da Guarita."""

import argparse
import asyncio
from collections.abc import Sequence

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server.stdio import stdio_server

from guarita import __version__
from guarita.catalog import PinCatalog
from guarita.gate import AllOf, ArgumentAllowlist, Gate
from guarita.integrity import PinnedTools
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
    stdio.add_argument("--catalog", help="arquivo SQLite do catálogo; exige --server")
    stdio.add_argument("--server", help="nome do servidor no catálogo")
    stdio.add_argument("upstream", nargs="+", help="comando do servidor MCP, depois de --")
    pin = commands.add_parser(
        "pin", help="fixa as definições atuais das ferramentas de um servidor"
    )
    pin.add_argument("--catalog", required=True, help="arquivo SQLite do catálogo")
    pin.add_argument("--server", required=True, help="nome do servidor no catálogo")
    pin.add_argument("upstream", nargs="+", help="comando do servidor MCP, depois de --")
    return parser


def upstream_params(command: list[str]) -> StdioServerParameters:
    return StdioServerParameters(command=command[0], args=command[1:])


async def pin_upstream(catalog_path: str, server: str, upstream_command: list[str]) -> list[str]:
    async with Client(upstream_params(upstream_command)) as upstream:
        listing = await upstream.list_tools()
    with PinCatalog(catalog_path) as catalog:
        return catalog.pin(server, listing.tools)


async def serve_stdio(
    upstream_command: list[str], gate: Gate, integrity: PinnedTools | None = None
) -> None:
    async with Client(upstream_params(upstream_command)) as upstream:
        server = build_proxy(upstream, gate, integrity)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stdio":
        if (args.catalog is None) != (args.server is None):
            raise SystemExit("guarita: --catalog e --server andam juntos")
        if args.catalog is None:
            asyncio.run(serve_stdio(args.upstream, AllOf(args.allow)))
        else:
            with PinCatalog(args.catalog) as catalog:
                integrity = PinnedTools(catalog, args.server)
                asyncio.run(serve_stdio(args.upstream, AllOf(args.allow), integrity))
    elif args.command == "pin":
        names = asyncio.run(pin_upstream(args.catalog, args.server, args.upstream))
        print(f"{len(names)} ferramenta(s) fixada(s) para {args.server}: {', '.join(names)}")
    return 0
