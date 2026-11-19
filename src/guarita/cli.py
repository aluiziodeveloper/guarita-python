"""Linha de comando da Guarita."""

import argparse
from collections.abc import Sequence

from guarita import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guarita",
        description="Firewall para agentes de IA que usam MCP.",
    )
    parser.add_argument("--version", action="version", version=f"guarita {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
