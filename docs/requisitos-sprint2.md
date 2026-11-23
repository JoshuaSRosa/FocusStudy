# Requisitos do Sprint 2 — avaliação e rastreabilidade (GRE2)

Este documento atende ao resultado **GRE2** do processo de Gerência de Requisitos:
os requisitos dos endpoints são avaliados com critérios objetivos e mantidos
rastreáveis até o código e os testes.

A fonte única dos IDs é `backend/tests/requirements_catalog.py`. O pytest recusa qualquer
teste marcado com um ID que não esteja lá, e `pytest --traceability` imprime a
matriz atualizada com o resultado de cada requisito. Ao alterar um requisito, atualize
os dois arquivos.

## 1. Critérios de avaliação

Cada requisito foi avaliado com três critérios. Um requisito só entra no Sprint se
atender aos três.

| Critério | Pergunta objetiva | Como se comprova |
|---|---|---|
| **Identificação única** | O requisito tem um ID que não se repete e não muda? | ID no catálogo `tests/requirements_catalog.py` (chave de dicionário: duplicata é impossível) |
| **Testabilidade** | Existe um resultado observável (código HTTP, campo, valor) que diz se ele foi atendido? | Critério de aceitação escrito como entrada → saída esperada (seção 2) |
| **Rastreabilidade** | Dá para ir do requisito até o código que o implementa e os testes que o verificam, e voltar? | Matriz da seção 3 + marcador `@pytest.mark.req` em cada teste |

## 2. Catálogo de requisitos e critérios de aceitação

Origem: **PO** = enunciado do Sprint 2 dado pela equipe; **S1** = funcionalidade do
Sprint 1 corrigida; **D** = requisito derivado (não estava no enunciado, mas é
necessário para os outros serem seguros e verificáveis).

| ID | Origem | Requisito | Critério de aceitação (testável) |
|---|---|---|---|
| FR-01 | PO | Cadastrar disciplina | `POST /api/courses` com `name` e `teacher` válidos → `201` e o objeto criado; faltando campo → `400` |
| FR-02 | PO | Listar/consultar disciplinas | `GET /api/courses` → `200` só com as disciplinas do usuário, em ordem alfabética (com acentos); `GET /{id}` inexistente → `404` |
| FR-03 | PO | Atualizar disciplina | `PUT /api/courses/{id}` → `200` com os novos dados; de outro usuário → `404` |
| FR-04 | PO | Excluir disciplina | `DELETE` → `200` e depois `GET` → `404`; com sessão aberta → `409` |
| FR-05 | PO | Upload de PDF | `POST /api/courses/{id}/pdf` com PDF válido → `201`, arquivo gravado e metadados no banco |
| FR-06 | PO | Registrar sessão (início/fim de Pomodoro) | `start` → `201`; `pause`/`resume`/`finish` → `200`; ação fora de ordem → `409` |
| FR-07 | PO | Histórico por disciplina | `GET /api/sessions?course={id}` → só sessões daquela disciplina, mais recentes primeiro, com `summary` |
| FR-08 | S1 | Cadastro de usuário | `POST /api/register` válido → `201`; duplicado → `409`; inválido → `400` (antes: `500`) |
| FR-09 | S1 | Login com JWT | credenciais corretas → `200` com `access_token`; erradas → `401` |
| BR-01 | PO | Disciplina única por usuário (nome + professor) | segunda disciplina com mesmo nome + professor, ignorando maiúsculas e espaços → `409`; outro usuário → `201` |
| BR-02 | PO | MIME do PDF validado no servidor | conteúdo não-PDF com `Content-Type: application/pdf` → `415` e nada gravado |
| BR-03 | PO | Timestamps gerados no servidor | `started_at`/`ended_at` enviados pelo cliente são ignorados; valores gravados = relógio do servidor (UTC) |
| BR-04 | PO | Tempo efetivo exclui pausas | 25 min foco + 5 min pausa + 25 min foco → `effective_seconds = 3000` |
| NFR-01 | D | Autenticação e isolamento | toda rota de disciplina/sessão sem token → `401`; recurso de outro usuário → `404` |
| NFR-02 | D | Erros padronizados | todo erro retorna JSON `{"status":"error","error":...}` com código 4xx/5xx adequado |
| VAL-01 | PO | Necessidade da equipe: registrar sessões de estudo | ver `docs/validacao-sprint2.md` |

### Decisões tomadas ao detalhar o enunciado

O enunciado deixava alguns pontos em aberto. As decisões abaixo foram tomadas para
tornar os requisitos testáveis e precisam ser confirmadas pela equipe na Sprint Review:

- **Nomenclatura em inglês.** O enunciado cita as rotas em português (`/api/disciplinas`,
  `/api/sessoes`). Por decisão da equipe, rotas, campos, banco e código foram padronizados
  em inglês (`/api/courses`, `/api/sessions`, `name`, `teacher`...). Os IDs de requisito
  seguem o mesmo padrão: **FR** (functional requirement, antes RF), **BR** (business rule,
  antes RN) e **NFR** (non-functional requirement, antes RNF). A correspondência com o
  enunciado é 1 para 1 e está na tabela da seção 2.
- **PUT/DELETE usam `/api/courses/{id}`.** O enunciado cita a rota da coleção, mas
  sem o id não há como saber qual disciplina alterar.
- **"Mesmo nome + professor"** compara sem diferenciar maiúsculas/minúsculas e
  ignorando espaços extras. "Cálculo I" e "calculo I" (sem acento) continuam sendo
  diferentes.
- **Início/fim de Pomodoro** foi modelado como uma sessão com ações `start`,
  `pause`, `resume` e `finish` no mesmo `POST /api/sessions`, pois a BR-04
  (descontar pausas) exige registrar as pausas.
- **Uma sessão aberta por usuário**, já que um estudante não foca em duas disciplinas ao
  mesmo tempo.
- **Excluir disciplina apaga seu histórico de sessões.** Alternativa, se a equipe
  preferir: bloquear a exclusão quando houver histórico.

## 3. Matriz de rastreabilidade

Requisito → implementação → testes. Os números são quantidades de funções de teste
(casos parametrizados contam uma vez aqui; a saída do `pytest --traceability` conta
cada caso).

| ID | Implementação | Testes (funções) |
|---|---|---|
| FR-01 | `api_blueprint/courses.py::create_course` | `test_courses.py` (4) |
| FR-02 | `courses.py::list_courses`, `get_course` | `test_courses.py` (3) |
| FR-03 | `courses.py::update_course` | `test_courses.py` (5) |
| FR-04 | `courses.py::delete_course` | `test_courses.py` (4), `test_pdf.py` (1) |
| FR-05 | `courses.py::upload_pdf`, tabela `pdfs` | `test_pdf.py` (5) |
| FR-06 | `api_blueprint/sessions.py::session_action`, `_start`; tabelas `sessions`, `pauses` | `test_sessions.py` (10), `test_courses.py` (1) |
| FR-07 | `sessions.py::history` | `test_sessions.py` (4) |
| FR-08 | `api_blueprint/auth.py::register`, `validations.py` | `test_auth.py` (6), `test_unit_validations.py` (4) |
| FR-09 | `auth.py::login` | `test_auth.py` (4) |
| BR-01 | `courses.py::_duplicate_exists` + índice `ux_courses_user_name_teacher` | `test_courses.py` (6), `test_unit_validations.py` (1) |
| BR-02 | `validations.py::validate_pdf`, `detect_mime` + CHECK na coluna `pdfs.mime` | `test_unit_validations.py` (4), `test_pdf.py` (2) |
| BR-03 | `clock.py::now`, uso em `sessions.py` | `test_sessions.py` (5) |
| BR-04 | `focus.py::calculate_focus_time` | `test_unit_focus.py` (11), `test_sessions.py` (5) |
| NFR-01 | `@jwt_required` + filtro `user_id` em todas as consultas | `test_courses.py` (6), `test_sessions.py` (3), `test_auth.py` (1), `test_pdf.py` (1) |
| NFR-02 | `api.py::error_response`, handlers em `main.py` | `test_auth.py` (6), `test_pdf.py` (3), `test_sessions.py` (3), `test_courses.py` (2) |
| VAL-01 | fluxo completo | `test_acceptance.py` (1) |

### Resultado da última execução

Saída de `pytest --traceability` (143 casos, 0 falhas, PostgreSQL 16):

```
ID       Tests  Pass  Fail  Skip  Status      Description
FR-01       11    11     0     0  VERIFIED    Create course (POST /api/courses)
FR-02        3     3     0     0  VERIFIED    List/get the user's courses (GET /api/courses[/id])
FR-03        5     5     0     0  VERIFIED    Update course (PUT /api/courses/{id})
FR-04        5     5     0     0  VERIFIED    Delete course (DELETE /api/courses/{id})
FR-05        5     5     0     0  VERIFIED    Upload a course PDF (POST /api/courses/{id}/pdf)
FR-06       22    22     0     0  VERIFIED    Record focus session: start/pause/resume/finish (POST /api/sessions)
FR-07        7     7     0     0  VERIFIED    Get session history, filterable by course (GET /api/sessions?course={id})
FR-08       29    29     0     0  VERIFIED    Register user (POST /api/register) - Sprint 1, fixed
FR-09        8     8     0     0  VERIFIED    Authenticate user and issue JWT (POST /api/login) - Sprint 1, fixed
BR-01       13    13     0     0  VERIFIED    A course cannot repeat name + teacher for the same user
BR-02       18    18     0     0  VERIFIED    PDF validated on the server: Content-Type application/pdf AND real PDF content
BR-03        5     5     0     0  VERIFIED    Start/end/pause timestamps generated by the server clock
BR-04       16    16     0     0  VERIFIED    Effective focus time = total duration - pauses
NFR-01      18    18     0     0  VERIFIED    Course/session routes require JWT and isolate data per user
NFR-02      43    43     0     0  VERIFIED    Errors return standardized JSON with the proper HTTP status
VAL-01       1     1     0     0  VERIFIED    Student records a study session with pauses and sees the effective time in the history
```

Situações possíveis: `VERIFIED` (todos os testes passaram), `FAILED` (algum falhou),
`INCOMPLETE` (algum teste foi pulado, por exemplo sem banco) e `NO TEST`
(requisito sem nenhum teste: não pode ser dado como pronto).

## 4. Avaliação final

| Critério | Resultado |
|---|---|
| Identificação única | 16 de 16 requisitos com ID único no catálogo |
| Testabilidade | 16 de 16 com critério de aceitação observável (seção 2) |
| Rastreabilidade | 16 de 16 com implementação localizada e ao menos 1 teste; nenhum `NO TEST` |
