from typing import Any

import pytest

from guarita.domain import Call, Decision, InvalidCallError, Verdict


@pytest.mark.parametrize("name", ["read_file", "files.read", "send-email", "a" * 128])
def test_accepts_valid_tool_names(name: str) -> None:
    assert Call(name).tool == name


@pytest.mark.parametrize(
    "name",
    ["", "read file", "read_file\n", "rm;ls", "a" * 129, "ler_arquivo_é"],
)
def test_refuses_invalid_tool_names(name: str) -> None:
    with pytest.raises(InvalidCallError, match="nome de ferramenta inválido"):
        Call(name)


@pytest.mark.parametrize("arguments", [["notes.txt"], "notes.txt", 42])
def test_refuses_arguments_that_are_not_an_object(arguments: Any) -> None:
    with pytest.raises(InvalidCallError, match="objeto JSON"):
        Call("read_file", arguments)


def test_arguments_cannot_change_after_validation() -> None:
    original = {"path": "notes.txt"}
    call = Call("read_file", original)
    original["path"] = "~/.ssh/id_rsa"

    assert call.arguments["path"] == "notes.txt"
    with pytest.raises(TypeError):
        call.arguments["path"] = "~/.ssh/id_rsa"  # type: ignore[index]


def test_decisions_say_whether_the_call_goes_on() -> None:
    assert Decision.allow().allowed is True
    denied = Decision.deny("fora da lista")
    assert denied.allowed is False
    assert denied.verdict is Verdict.DENY
    assert denied.reason == "fora da lista"
