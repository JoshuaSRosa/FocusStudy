# Sprint 2 — ciclo de vida e entrega incremental (GPR3)

Este documento registra como o Sprint 2 se encaixa no ciclo de vida ágil definido
para o projeto (resultado **GPR3** da Gerência de Projetos): Sprints de **1 semana e
meia**, cada uma terminando com um incremento funcionando e verificado.

> Os campos entre colchetes devem ser preenchidos pela equipe com as datas e os
> responsáveis reais. O conteúdo técnico (backlog, DoD, incremento) já reflete o que
> foi entregue.

## Identificação

| Campo | Valor |
|---|---|
| Sprint | 2 |
| Duração | 1,5 semana — de [__/__/____] a [__/__/____] |
| Objetivo | O estudante consegue cadastrar disciplinas, anexar PDFs e registrar sessões de foco com o tempo efetivo calculado pelo servidor |
| Incremento anterior | Sprint 1: estrutura Docker, cadastro e login (com defeitos, ver B-01 a B-10) |

## Cerimônias

| Cerimônia | Quando | Saída |
|---|---|---|
| Planning | Dia 1 | Backlog abaixo, requisitos com ID e critério de aceitação (`requisitos-sprint2.md`) |
| Daily | Diária, 15 min | Impedimentos registrados |
| Review | Último dia | Demonstração e termo de aceite (`validacao-sprint2.md`) |
| Retrospectiva | Último dia | Melhorias de processo (seção final de `pdca-sprint2.md`) |

## Backlog do Sprint

Distribuição sugerida para 1,5 semana (≈ 7 dias úteis). A coluna "Responsável" é da equipe.

| # | Item | Requisitos | Dias | Responsável | Situação |
|---|---|---|---|---|---|
| 1 | Corrigir schema, cadastro, login e docker-compose do Sprint 1 | FR-08, FR-09 | 1–2 | [ ] | Pronto |
| 2 | CRUD de disciplinas com regra de duplicidade | FR-01..04, BR-01 | 2–3 | [ ] | Pronto |
| 3 | Upload de PDF com validação no servidor | FR-05, BR-02 | 3–4 | [ ] | Pronto |
| 4 | Sessões: iniciar/pausar/retomar/finalizar | FR-06, BR-03 | 4–5 | [ ] | Pronto |
| 5 | Cálculo de tempo efetivo e histórico | BR-04, FR-07 | 5–6 | [ ] | Pronto |
| 6 | Testes, matriz de rastreabilidade, correções | todos | 6–7 | [ ] | Pronto |
| 7 | Review com a equipe (validação) | VAL-01 | 7 | [ ] | **Pendente** |

## Definição de Pronto (DoD)

Um item só é considerado pronto quando:

1. o requisito tem ID e critério de aceitação no catálogo;
2. existe pelo menos um teste marcado com o ID (`@pytest.mark.req`);
3. `pytest` passa sem falhas contra PostgreSQL (não vale "pulado");
4. a matriz `pytest --traceability` mostra o requisito como `VERIFIED`;
5. o endpoint está documentado em `docs/API.md`;
6. sobe com `docker compose up` sem passos manuais;
7. a suíte foi executada **depois da última alteração** de código (um resultado antigo não vale:
   ver defeitos B-16 e B-17 em `pdca-sprint2.md`).

Situação do Sprint 2 frente à DoD: itens 1 a 7 cumpridos para todos os requisitos
(última execução: 143 passaram, 0 falharam, após corrigir B-16 e B-17 e padronizar a
nomenclatura em inglês).
Falta a Review (item 7 do backlog) para fechar a validação.

## Incremento entregue

| Sprint 1 | Sprint 2 (este incremento) |
|---|---|
| Containers do banco e do backend | Containers **conectando de fato** (rede corrigida) + volume para PDFs + serviço de testes |
| Cadastro e login (falhando) | Cadastro e login funcionando, senha com hash e sal, JWT |
| — | CRUD de disciplinas com BR-01 |
| — | Upload de PDF com BR-02 |
| — | Sessões de foco com pausas, BR-03 e BR-04 |
| — | Histórico por disciplina com total estudado |
| — | 143 testes automatizados, 93% de cobertura, matriz de rastreabilidade |

**Mudanças que afetam o frontend:**

- respostas de sucesso usam `"status": "success"` (o login respondia `"sucess"`);
- erros de validação retornam `400` e duplicidade `409` (antes, quase tudo era `401`);
- `/register` responde `201` em vez de `200`;
- **nomenclatura em inglês**: rotas `/api/courses` e `/api/sessions` (antes `/api/disciplinas`
  e `/api/sessoes`), campos `name`/`teacher`, `action` com `start`/`pause`/`resume`/`finish`,
  `course_id`, `session_id`, `started_at`/`ended_at`, `effective_seconds`, `summary`, upload no
  campo `file`, cadastro com `program` (antes `curso`) e mensagens de erro em inglês
  (contrato completo em `docs/API.md`);
- PUT e DELETE de disciplina usam `/api/courses/{id}`;
- o `identity` do JWT agora é o id do usuário; o nome aparece em `logged_as`.

## Levado para o Sprint 3 (sugestões)

| Item | Motivo |
|---|---|
| Listar e baixar os PDFs de uma disciplina | O Sprint 2 cobre apenas o envio |
| Paginação e filtro por período no histórico | O histórico cresce sem limite |
| Testes de concorrência e CI no GitHub Actions | Linhas de proteção contra corrida ainda sem teste (ver cobertura) |
| Limite de tentativas de login | Proteção contra força bruta |
| Ajustes vindos do termo de aceite | Resultado da Review |
