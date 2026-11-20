"""Política como código em TOML com negação por padrão (default-deny)."""

import fnmatch
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any
from urllib.parse import unquote

from guarita.domain import Call, Decision


class PolicyError(ValueError):
    """Arquivo de política inválido: falha fechada na carga."""


class Effect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


def _has_traversal(value: str) -> bool:
    decoded = value
    for _ in range(2):
        decoded = unquote(decoded)
    return ".." in PurePosixPath(decoded.replace("\\", "/")).parts


def _argument_matches(value: Any, patterns: tuple[str, ...]) -> bool:
    if not isinstance(value, str):
        return False
    if _has_traversal(value):
        return False
    return any(fnmatch.fnmatchcase(value, pat) for pat in patterns)


@dataclass(frozen=True)
class Rule:
    effect: Effect
    tools: tuple[str, ...]
    reason: str = ""
    agents: tuple[str, ...] = ()
    arguments: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: MappingProxyType({}))

    def matches(self, call: Call) -> bool:
        if self.agents and call.agent not in self.agents and "*" not in self.agents:
            return False
        if call.tool not in self.tools and "*" not in self.tools:
            return False
        for key, patterns in self.arguments.items():
            if key not in call.arguments or not _argument_matches(call.arguments[key], patterns):
                return False
        return True


def _parse_rule(raw: dict[str, Any]) -> Rule:
    try:
        effect = Effect(raw["effect"])
    except (KeyError, ValueError) as error:
        raise PolicyError(f"efeito inválido na regra: {raw!r}") from error
    tools = raw.get("tools")
    if not isinstance(tools, list) or not tools or not all(isinstance(t, str) for t in tools):
        raise PolicyError(f"a regra precisa listar ao menos uma ferramenta: {raw!r}")
    agents = raw.get("agents", [])
    if not isinstance(agents, list) or not all(isinstance(a, str) for a in agents):
        raise PolicyError(f"'agents' precisa ser lista de strings: {raw!r}")
    raw_args = raw.get("arguments", {})
    if not isinstance(raw_args, dict):
        raise PolicyError(f"'arguments' precisa ser uma tabela: {raw!r}")
    parsed_args: dict[str, tuple[str, ...]] = {}
    for k, v in raw_args.items():
        if not isinstance(v, list) or not v or not all(isinstance(p, str) for p in v):
            raise PolicyError(f"padrões inválidos para argumento {k!r}: {v!r}")
        parsed_args[str(k)] = tuple(v)
    return Rule(
        effect=effect,
        tools=tuple(tools),
        reason=str(raw.get("reason", "")),
        agents=tuple(agents),
        arguments=MappingProxyType(parsed_args),
    )


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
