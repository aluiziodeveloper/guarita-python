"""Tipos de domínio da Guarita: a chamada de ferramenta e a decisão sobre ela."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

# Nomes de ferramenta aceitos pelo MCP: letras, dígitos, "_", "-" e ".", até 128 caracteres.
TOOL_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")


class InvalidCallError(ValueError):
    """A chamada chegou malformada e nem chega a ser avaliada."""


class Verdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class Call:
    """Uma chamada de ferramenta, já validada na borda."""

    tool: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    agent: str = "anonymous"

    def __post_init__(self) -> None:
        if not TOOL_NAME.fullmatch(self.tool):
            raise InvalidCallError(f"nome de ferramenta inválido: {self.tool!r}")
        if not isinstance(self.arguments, Mapping):
            raise InvalidCallError("os argumentos precisam ser um objeto JSON")
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str = ""

    @classmethod
    def allow(cls) -> Decision:
        return cls(Verdict.ALLOW)

    @classmethod
    def deny(cls, reason: str) -> Decision:
        return cls(Verdict.DENY, reason)

    @classmethod
    def ask(cls, reason: str) -> Decision:
        return cls(Verdict.ASK, reason)

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW
