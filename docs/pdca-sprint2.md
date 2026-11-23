# Ciclo PDCA do Sprint 2 e Verificação (ISO/IEC 12207)

**Verificação** responde: *a API foi construída corretamente?* Ou seja, ela cumpre
o que os requisitos especificam? É feita com testes automatizados (pytest).
**Validação** (a API resolve a necessidade da equipe?) está em `docs/validacao-sprint2.md`.

O trabalho do Sprint seguiu o ciclo PDCA abaixo.

---

## P — Plan (planejar)

1. **Inventário do que existia.** Antes de planejar o novo, o código do Sprint 1 foi
   executado contra um PostgreSQL 16 real. Os defeitos encontrados (seção "Act")
   entraram no backlog, porque os endpoints novos dependem de cadastro e login funcionando.
2. **Endpoints definidos**, cada um com ID e critério de aceitação
   (`docs/requisitos-sprint2.md`), e contrato documentado (`docs/API.md`).
3. **Modelo de dados**: tabelas `courses`, `pdfs`, `sessions` e `pauses`; as regras de
   negócio também são garantidas no banco (índice único para BR-01, CHECK para BR-02,
   no máximo uma sessão aberta por usuário).
4. **Estratégia de verificação**:

| Nível | O que verifica | Arquivos | Precisa de banco? |
|---|---|---|---|
| Unidade | Regras puras: cálculo de foco (BR-04), validações, detecção de PDF (BR-02) | `test_unit_*.py` | Não |
| Endpoint | Cada rota via cliente de teste do Flask, contra PostgreSQL real | `test_auth.py`, `test_courses.py`, `test_pdf.py`, `test_sessions.py` | Sim |
| Aceitação | Fluxo completo do estudante (VAL-01) | `test_acceptance.py` | Sim |

   Decisões que tornam o código testável:
   - o relógio do servidor fica em `clock.py`, e os testes o substituem por um relógio
     controlado, para verificar durações exatas sem `sleep`;
   - o cálculo de tempo efetivo é uma função pura (`focus.py`);
   - os testes usam um banco separado (`focusstudy_test`) recriado a partir do próprio
     `database/init.sql`, que assim também é verificado; o conftest se recusa a rodar em
     banco cujo nome não termine em `_test`.

5. **Critério de saída do Check**: 0 testes falhando e nenhum requisito `NO TEST`
   ou `INCOMPLETE` na matriz de rastreabilidade.

## D — Do (executar)

| Item | Arquivos |
|---|---|
| CRUD de disciplinas + BR-01 | `api_blueprint/courses.py` |
| Upload de PDF + BR-02 | `api_blueprint/courses.py`, `validations.py` |
| Sessões e histórico + BR-03, BR-04 | `api_blueprint/sessions.py`, `clock.py`, `focus.py` |
| Cadastro/login corrigidos | `api_blueprint/auth.py` |
| Transações com commit/rollback e devolução da conexão | `database.py` (`transaction()`) |
| App factory, erros em JSON, limite de upload | `main.py` |
| Schema PostgreSQL | `database/init.sql` |
| Rede Docker, volume de PDFs, serviço de testes | `docker-compose.yml`, `backend/Dockerfile` |

## C — Check (verificar)

Comando: `pytest --traceability --cov=.`

**Primeira execução: 142 passaram, 1 falhou.**
`test_list_returns_only_user_courses_sorted` esperava
`["Álgebra", "Física"]` e recebeu `["Física", "Álgebra"]` (defeito B-11, abaixo).

**Segunda execução (após corrigir B-11): 143 passaram, 0 falharam.**

**Terceira execução (reverificação antes da Review): 95 passaram, 30 falharam, 18 erros.**
`api_blueprint/courses.py` foi alterado *depois* da segunda execução, sem rodar os
testes de novo. Todas as 48 falhas tinham uma única origem (defeitos B-16 e B-17): o
`POST /api/courses` respondia `400` para qualquer requisição válida, e por isso também
quebravam os testes de PDF, de sessões e de aceitação, que precisam criar uma disciplina
antes. A matriz mostrou FR-01..FR-07, BR-01..BR-04 e VAL-01 como `FAILED`/`INCOMPLETE`.

**Quarta execução (após corrigir B-16 e B-17): 143 passaram, 0 falharam.**

**Quinta execução (após padronizar a nomenclatura em inglês): 143 passaram, 0 falharam**,
mesma cobertura e mesmas contagens por requisito. Todos os 16 requisitos com
situação `VERIFIED` (matriz completa em `docs/requisitos-sprint2.md`).

Cobertura de código da aplicação (sem contar os testes): **93%**.

| Módulo | Cobertura | Linhas não cobertas |
|---|---|---|
| `focus.py`, `validations.py`, `clock.py`, `api_blueprint/api.py` | 100% | — |
| `api_blueprint/sessions.py` | 98% | tratamento de `UniqueViolation` em dois "iniciar" simultâneos |
| `api_blueprint/auth.py` | 97% | tratamento de `UniqueViolation` em dois cadastros simultâneos |
| `api_blueprint/courses.py` | 90% | mesmas proteções contra concorrência; falha de disco ao apagar PDF |
| `main.py` | 87% | erro 500 genérico, token expirado, `JWT_SECRET_KEY` ausente |
| `database.py` | 74% | descarte de conexão quebrada quando o Postgres reinicia |

As linhas não cobertas são, em sua maioria, proteções contra condições de corrida,
que precisariam de testes concorrentes (sugestão para o Sprint 3).

Verificações manuais complementares:
- `database/init.sql` aplicado num banco vazio sem erros;
- API executada com **gunicorn** (`main:create_app()`, como no container): cadastro,
  login, disciplina, upload de PDF real (`201`), executável renomeado para `.pdf` (`415`),
  sessão iniciada e finalizada, histórico;
- com o banco fora do ar, a API responde `503` em JSON em vez de travar;
- sem PostgreSQL, os 46 testes de unidade rodam e os 97 de endpoint são **pulados com o
  motivo** (não aparecem como aprovados).

## A — Act (agir/corrigir)

Defeitos encontrados e corrigidos. Os que têm "Evidência" foram reproduzidos executando
o código original antes da correção. Arquivos, funções e testes aparecem com os nomes
atuais, em inglês (ver "Padronização da nomenclatura"); B-16 e B-17 citam os nomes da época
porque o defeito era justamente a divergência entre eles.

| ID | Defeito | Evidência / impacto | Correção | Teste de regressão |
|---|---|---|---|---|
| B-01 | `init.sql` usa `USE` e `IDENTITY(1,1)` (sintaxe de MySQL/SQL Server) | `ERROR: syntax error at or near "USE"`: a inicialização falhava e, após o restart, o banco subia **sem nenhuma tabela** | Reescrito para PostgreSQL, sem `CREATE DATABASE` (a imagem já cria o `POSTGRES_DB`) | `conftest.py` aplica o `init.sql` em toda execução |
| B-02 | `jsonify({"status", "..."})` cria um *set*, não um dict | `TypeError: Object of type set is not JSON serializable` → `500` | Resposta de erro padronizada `error_response()` | `test_register_missing_fields_returns_400_json` |
| B-03 | `cursor_factory=RealDictConnection` (deveria ser `RealDictCursor`) | `TypeError: argument 1 must be str` → **todo** register e login válidos davam `500` | `database.transaction()` usa `RealDictCursor` | todos os testes de `test_auth.py` |
| B-04 | Placeholders `?` (SQLite) em vez de `%s` (psycopg2) | toda consulta falharia | `%s` em todas as consultas | todos os testes de endpoint |
| B-05 | Checagem de duplicidade: parâmetros trocados, `data[0] == username` compara dict com str, `data[0]` em lista vazia | cadastro de usuário novo daria `IndexError`; duplicado nunca seria detectado | Consulta com flags `user_dup`/`email_dup`, sem diferenciar maiúsculas | `test_register_duplicate_returns_409` (4 casos) |
| B-06 | `INSERT INTO users VALUES (?, ?, ?, ?)` sem colunas, na ordem errada, sem `commit`; tabela sem coluna `username` | nenhum usuário seria gravado | Colunas explícitas, `RETURNING id`, commit automático em `transaction()` | `test_register_success_via_form_stores_salted_hash` |
| B-07 | Login consulta a coluna `password` (a coluna é `senha_hash`), passa `(user)` em vez de `(user,)` e compara dict com hash | login impossível | Consulta por email **ou** username + `check_password_hash` | `test_login_by_email_or_username` (4 casos) |
| B-08 | Senha com SHA-256 sem sal | vulnerável a tabelas pré-computadas | `werkzeug.security` (scrypt com sal); sem dependência nova | `test_register_success_via_form_stores_salted_hash` |
| B-09 | Conexões não devolvidas ao pool nos `return` antecipados e no login | após 20 requisições, o pool se esgotaria (`PoolError`) e toda rota com banco passaria a falhar | Gerenciador de contexto `transaction()` sempre devolve a conexão | todas as rotas usam `transaction()` |
| B-10 | `docker-compose.yml`: backend com `DB_HOST=localhost` e `DB_PORT=5433` | dentro do container, `localhost` é o próprio backend: **a API nunca conectava ao banco** | `DB_HOST=database`, `DB_PORT=5432` (nome do serviço e porta interna) | smoke test com gunicorn |
| B-11 | Ordenação alfabética punha "Álgebra" depois de "Física" | **achado no Check deste Sprint**: com collation "C" (a do ambiente de teste; a musl do `postgres:16-alpine` também não ordena acentos), letras acentuadas vão para o fim | `ORDER BY name COLLATE "und-x-icu"` | `test_list_returns_only_user_courses_sorted` |
| B-12 | Erros de validação e de banco retornavam `401` | o frontend trataria "email inválido" como "não autenticado" | `400` validação, `409` conflito, `503` banco fora | testes marcados com `NFR-02` |
| B-13 | `/login` exigia usuário e senha mesmo com token válido, contrariando `instructions.txt` | — | O token é verificado primeiro | `test_login_with_valid_token_does_not_require_password` |
| B-14 | `PUT`/`DELETE /courses` sem `{id}` na rota | impossível saber o que alterar | `/courses/<int:id>` | testes de FR-03 e FR-04 |
| B-16 | O endpoint de disciplinas lia o campo `name`, mas o contrato da época (API.md e testes) definia `nome` | **achado na reverificação**: todo cadastro/atualização de disciplina respondia `400`; o estudante não conseguiria usar nada do Sprint 2 | Campo alinhado ao contrato (hoje `name` em todo o sistema, ver "Padronização da nomenclatura") | `test_create_course_returns_201_with_data` e outros 47 |
| B-17 | A serialização usava as chaves `name`, `created`, `updated`, que não existiam no resultado da consulta (as colunas eram `nome`, `criado_em`, `atualizado_em`) | `KeyError` → `500` em toda leitura de disciplina (ficava escondido atrás do B-16) | Chaves iguais às colunas do `init.sql` (hoje `name`, `created_at`, `updated_at`) | `test_list_returns_only_user_courses_sorted`, `test_get_by_id_and_isolation` |
| B-15 | `SimpleConnectionPool` não é seguro com threads; `debug=True` fixo | — | `ThreadedConnectionPool`; debug só com `FLASK_DEBUG=1` | — |

### Padronização da nomenclatura (novo ciclo PDCA)

Os defeitos B-16 e B-17 nasceram de uma troca **parcial** de nomes do português para o
inglês. Para eliminar a causa, toda a nomenclatura técnica foi padronizada em inglês, num
ciclo PDCA próprio:

- **Plan:** glossário único aplicado a banco, API, código e testes, por exemplo:
  `disciplinas` → `courses`, `nome` → `name`, `professor` → `teacher`, `sessoes` → `sessions`,
  `pausas` → `pauses`, `inicio`/`fim` → `started_at`/`ended_at`, ações
  `iniciar`/`pausar`/`retomar`/`finalizar` → `start`/`pause`/`resume`/`finish`,
  status `em_andamento`/`pausada`/`finalizada` → `in_progress`/`paused`/`finished`,
  `curso` do usuário → `program`, IDs `RF`/`RN`/`RNF` → `FR`/`BR`/`NFR`.
  O comportamento não muda: a refatoração só é aceita se a suíte der o mesmo resultado.
- **Do:** renomeados schema (`init.sql`), módulos (`courses.py`, `sessions.py`, `focus.py`,
  `clock.py`, `validations.py`), funções, rotas, campos JSON, mensagens de erro e testes.
- **Check:** 143 passaram, 0 falharam; as contagens por requisito na matriz e a cobertura
  (93%) ficaram idênticas às de antes da troca, o que mostra que o comportamento foi preservado.
  O roteiro da Review foi refeito por HTTP com a API nova (ver `validacao-sprint2.md`).
- **Act:** documentação atualizada; mudança registrada para o frontend em `sprint2-gpr3.md`.
  Bancos criados com o schema antigo precisam ser recriados (`docker compose down -v`).

### Melhorias de processo para o próximo ciclo

- **Lição do B-16/B-17:** um resultado de teste só vale para o código exatamente como estava
  quando foi executado. Toda alteração depois do Check exige rodar a suíte de novo antes
  de declarar o item pronto (regra incluída na DoD, item 7, em `sprint2-gpr3.md`).
- Rodar `pytest` antes de todo merge (no CI, com `docker compose --profile test run --rm tests`).
  Os defeitos B-02 a B-07 teriam sido pegos na primeira execução.
- Não marcar uma história como pronta sem pelo menos um teste por requisito
  (situação diferente de `NO TEST` na matriz).
- Ao trocar de banco ou imagem Docker, testar contra a mesma imagem de produção (B-11 só
  aparece com a collation real).
