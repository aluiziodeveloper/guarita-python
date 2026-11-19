"""O portão: quem decide se uma chamada de ferramenta segue para o servidor."""

from collections.abc import Iterable
from typing import Protocol

from guarita.domain import Call, Decision


class Gate(Protocol):
    async def decide(self, call: Call) -> Decision: ...


class AllowAll:
    """Portão aberto: o proxy transparente da aula 02-02."""

    async def decide(self, call: Call) -> Decision:
        return Decision.allow()


class ArgumentAllowlist:
    """Só deixa passar a ferramenta com o argumento dentro de uma lista de valores aceitos."""

    def __init__(self, tool: str, argument: str, allowed: Iterable[str]) -> None:
        self._tool = tool
        self._argument = argument
        self._allowed = frozenset(allowed)

    async def decide(self, call: Call) -> Decision:
        if call.tool != self._tool:
            return Decision.allow()
        value = call.arguments.get(self._argument)
        if value in self._allowed:
            return Decision.allow()
        return Decision.deny(f"{self._argument}={value!r} fora da lista de {self._tool}")
