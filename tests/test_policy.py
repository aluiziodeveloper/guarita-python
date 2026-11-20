import pytest

from guarita.domain import Call, Verdict
from guarita.policy import PolicyError, PolicyGate

pytestmark = pytest.mark.anyio


async def test_denies_by_default_when_no_rule_matches() -> None:
    gate = PolicyGate.from_toml("")

    decision = await gate.decide(Call("read_file", {"path": "notes.txt"}))

    assert decision.allowed is False
    assert decision.verdict is Verdict.DENY
    assert "padrão" in decision.reason


async def test_allows_a_tool_listed_in_an_allow_rule() -> None:
    gate = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        tools = ["read_file"]
        """
    )

    allowed = await gate.decide(Call("read_file", {"path": "notes.txt"}))
    denied = await gate.decide(Call("delete_file", {"path": "notes.txt"}))

    assert allowed.allowed is True
    assert denied.allowed is False


async def test_deny_wins_over_ask_and_allow() -> None:
    gate = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        tools = ["read_file", "send_email"]

        [[rules]]
        effect = "ask"
        tools = ["send_email"]
        reason = "envio externo pede operador"

        [[rules]]
        effect = "deny"
        tools = ["read_file"]
        reason = "leitura bloqueada neste perfil"
        """
    )

    read = await gate.decide(Call("read_file", {}))
    mail = await gate.decide(Call("send_email", {}))

    assert read.verdict is Verdict.DENY
    assert "leitura bloqueada" in read.reason
    assert mail.verdict is Verdict.ASK
    assert mail.allowed is False


@pytest.mark.parametrize(
    "bad_toml",
    [
        "[[rules]\n",
        '[[rules]]\neffect = "maybe"\ntools = ["read_file"]\n',
        '[[rules]]\neffect = "allow"\ntools = []\n',
    ],
)
def test_refuses_invalid_policy_definitions(bad_toml: str) -> None:
    with pytest.raises(PolicyError):
        PolicyGate.from_toml(bad_toml)


async def test_matches_rules_by_agent_and_argument_globs() -> None:
    gate = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        agents = ["support-bot"]
        tools = ["read_file"]
        [rules.arguments]
        path = ["notes/*.txt", "notes.txt"]
        """
    )

    ok = await gate.decide(Call("read_file", {"path": "notes/q4.txt"}, agent="support-bot"))
    wrong_agent = await gate.decide(Call("read_file", {"path": "notes/q4.txt"}, agent="intern-bot"))
    wrong_path = await gate.decide(
        Call("read_file", {"path": "~/.ssh/id_rsa"}, agent="support-bot")
    )

    assert ok.allowed is True
    assert wrong_agent.allowed is False
    assert wrong_path.allowed is False


async def test_blocks_path_traversal_against_glob_patterns() -> None:
    gate = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        tools = ["read_file"]
        [rules.arguments]
        path = ["notes/*"]
        """
    )

    traversal = await gate.decide(Call("read_file", {"path": "notes/../.ssh/id_rsa"}))

    assert traversal.allowed is False
