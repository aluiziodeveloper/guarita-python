# ADR 0002 · Política como código em TOML com negação por padrão

- **Estado:** aceito
- **Módulo:** 04 (Política, menor privilégio e aprovação humana)

## Contexto

Passar regras de permissão com `--allow` na linha de comando não escala para vários agentes,
várias ferramentas e efeitos diferentes (`allow`, `ask`, `deny`). Precisávamos de uma política
versionável em arquivo, testável e com falha fechada.

## Decisão

Adotar arquivos TOML lidos por `tomllib` (biblioteca padrão do Python 3.14), com precedência
explícita (`deny` > `ask` > `allow`) e negação por padrão (*default-deny*).

## Consequências

- Zero dependência externa e nenhuma segunda linguagem (como Rego) para o aluno aprender.
- A mesma ideia de política declarativa, versionada em Git e provada por testes unitários continua
  exatamente igual; quem precisar de OPA/Rego em escala corporativa troca apenas o adaptador atrás
  da porta `Gate`.
