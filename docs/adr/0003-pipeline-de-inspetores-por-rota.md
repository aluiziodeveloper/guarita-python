# ADR 0003 · Pipeline de inspetores por rota

- **Estado:** aceito
- **Módulo:** 07 (Contenção e limites)

## Contexto

Com política, aprovação, validação de esquema, DLP, controle de destinos, detector de injeção,
marcação não confiável e classificador local, encadear tudo manualmente no `build_proxy` viraria
um emaranhado difícil de manter e configuraria o mesmo custo de inspeção para toda ferramenta.

## Decisão

Criar `RoutePipeline` (sequências ordenadas de `Gate` na ida e `ResultReviewer` na volta, com
curto-circuito na primeira negação) e `PipelineRouter`, que escolhe o pipeline por padrão de nome
de ferramenta e implementa as duas portas (`Gate` e `ResultReviewer`).

## Consequências

- O `build_proxy` continua simples: recebe um `gate` e um `reviewer`.
- Ferramentas de leitura de dados externos recebem a cadeia completa na volta, enquanto ferramentas
  sensíveis de envio recebem DLP + egress + aprovação na ida.
