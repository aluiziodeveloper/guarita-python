"""Política como código em TOML com negação por padrão (default-deny)."""

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from guarita.domain import Call, Decision


class PolicyError(ValueError):
    """Arquivo de política inválido: falha fechada na carga."""


class Effect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class Rule:
    effect: Effect
    tools: tuple[str, ...]
    reason: str = ""

    def matches(self, call: Call) -> bool:
        return call.tool in self.tools or "*" in self.tools


def _parse_rule(raw: dict[str, Any]) -> Rule:
    try:
        effect = Effect(raw["effect"])
    except (KeyError, ValueError) as error:
        raise PolicyError(f"efeito inválido na regra: {raw!r}") from error
    tools = raw.get("tools")
    if not isinstance(tools, list) or not tools or not all(isinstance(t, str) for t in tools):
        raise PolicyError(f"a regra precisa listar ao menos uma ferramenta: {raw!r}")
    reason = str(raw.get("reason", ""))
    return Rule(effect=effect, tools=tuple(tools), reason=reason)


class PolicyGate:
    """Avalia uma chamada contra regras TOML; sem regra favorável, nega por padrão."""

    def __init__(self, rules: tuple[Rule, ...]) -> None:
        self._rules = rules

    @classmethod
    def from_toml(cls, text: str) -> PolicyGate:
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise PolicyError(f"TOML inválido: {error}") from error
        raw_rules = data.get("rules", [])
        if not isinstance(raw_rules, list):
            raise PolicyError("'rules' precisa ser uma lista de tabelas [[rules]]")
        return cls(tuple(_parse_rule(r) for r in raw_rules))

    @classmethod
    def from_file(cls, path: str | Path) -> PolicyGate:
        return cls.from_toml(Path(path).read_text(encoding="utf-8"))

    async def decide(self, call: Call) -> Decision:
        matched = [rule for rule in self._rules if rule.matches(call)]
        for rule in matched:
            if rule.effect is Effect.DENY:
                return Decision.deny(rule.reason or f"negado pela política para {call.tool}")
        for rule in matched:
            if rule.effect is Effect.ASK:
                return Decision.ask(rule.reason or f"aprovação exigida para {call.tool}")
        for rule in matched:
            if rule.effect is Effect.ALLOW:
                return Decision.allow()
        return Decision.deny(f"negado por padrão pela política: {call.tool}")
