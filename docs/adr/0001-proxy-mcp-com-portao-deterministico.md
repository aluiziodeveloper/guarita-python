# ADR 0001: proxy MCP com portão determinístico

- **Estado:** aceita
- **Data:** aula 02-05

## Contexto

No laboratório, uma descrição de ferramenta envenenada leva o agente a pedir `~/.ssh/id_rsa`
mesmo com um pedido benigno. Pedir ao modelo que ignore instruções suspeitas deixaria a decisão
dentro do componente que acabou de ser enganado.

## Decisão

A Guarita fica entre o agente e os servidores MCP, como um proxy feito com o SDK oficial
(`mcp` 2.x). Toda chamada `tools/call` é validada na borda (`Call`) e passa por um portão
(`Gate`) antes de seguir. O portão é código determinístico e testável; o modelo não participa
da decisão.

## Consequências

- Uma chamada negada nunca chega ao servidor, e o agente recebe um erro de ferramenta.
- Cada defesa nova entra como um portão ou um inspetor, com teste de ataque.
- A Guarita precisa acompanhar as mudanças do protocolo e do SDK.
