import argparse
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.types import TextContent

from guarita.cli import main, parse_allow, pin_upstream
from guarita.domain import Call


def test_version_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == "guarita 0.1.0\n"


def test_without_arguments_exits_with_zero() -> None:
    assert main([]) == 0


@pytest.mark.anyio
async def test_parse_allow_builds_an_allowlist() -> None:
    gate = parse_allow("read_file:path=notes.txt,todo.txt")

    assert (await gate.decide(Call("read_file", {"path": "todo.txt"}))).allowed
    assert not (await gate.decide(Call("read_file", {"path": "~/.ssh/id_rsa"}))).allowed


@pytest.mark.parametrize("spec", ["read_file", "read_file:path", "read_file:=x", ":path=x"])
def test_parse_allow_refuses_incomplete_specs(spec: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_allow(spec)


@pytest.mark.anyio
async def test_guards_a_real_server_over_stdio() -> None:
    guarita = StdioServerParameters(
        command=sys.executable,
        args=[
            *["-m", "guarita", "stdio", "--allow", "read_file:path=notes.txt", "--"],
            *[sys.executable, "-m", "guarita.lab.server", "--variant", "poisoned"],
        ],
    )
    async with Client(guarita) as agent_side:
        allowed = await agent_side.call_tool("read_file", {"path": "notes.txt"})
        denied = await agent_side.call_tool("read_file", {"path": "~/.ssh/id_rsa"})

    assert allowed.is_error is False
    assert denied.is_error is True
    block = denied.content[0]
    assert isinstance(block, TextContent)
    assert block.text.startswith("Guarita: chamada negada")


def test_pin_records_the_tools_of_a_real_server(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = tmp_path / "catalog.db"
    lab = [sys.executable, "-m", "guarita.lab.server"]

    assert main(["pin", "--catalog", str(catalog), "--server", "files", "--", *lab]) == 0
    assert capsys.readouterr().out == "1 ferramenta(s) fixada(s) para files: read_file\n"


@pytest.mark.anyio
async def test_stdio_with_a_catalog_denies_the_rug_pull(tmp_path: Path) -> None:
    catalog = str(tmp_path / "catalog.db")
    lab = [sys.executable, "-m", "guarita.lab.server", "--variant", "rug-pull"]
    assert await pin_upstream(catalog, "files", lab) == ["read_file"]
    guarita = StdioServerParameters(
        command=sys.executable,
        args=["-m", "guarita", "stdio", "--catalog", catalog, "--server", "files", "--", *lab],
    )
    async with Client(guarita) as agent_side:
        first = await agent_side.call_tool("read_file", {"path": "notes.txt"})
        second = await agent_side.call_tool("read_file", {"path": "notes.txt"})

    assert first.is_error is False
    assert second.is_error is True


def test_catalog_without_server_is_refused() -> None:
    with pytest.raises(SystemExit, match="andam juntos"):
        main(["stdio", "--catalog", "x.db", "--", "true"])
