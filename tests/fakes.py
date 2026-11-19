"""Dublês compartilhados pelos testes."""

from guarita.lab.model import Message, ModelReply, ToolSpec


class ScriptedModel:
    """Modelo de mentira: devolve as respostas na ordem e guarda o que recebeu."""

    def __init__(self, *replies: ModelReply) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[list[Message], list[ToolSpec]]] = []

    async def chat(self, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        self.calls.append(([dict(m) for m in messages], tools))
        return self.replies.pop(0)
