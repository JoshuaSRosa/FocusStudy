# FocusStudy — Referência da API (Sprint 2)

Base: `http://localhost:8080/api`

Todas as respostas são JSON. Sucesso traz `"status": "success"`; erro traz
`"status": "error"` e uma mensagem em `"error"` (NFR-02). Rotas, campos e
mensagens da API são em inglês.

Rotas marcadas com 🔒 exigem o header `Authorization: Bearer <access_token>`
obtido no `/login`. Um usuário só enxerga e altera os próprios dados: recurso
de outro usuário responde **404**, como se não existisse (NFR-01).

Os corpos podem ser enviados como JSON ou como formulário, exceto o upload de PDF,
que é `multipart/form-data`.

## Códigos HTTP usados

| Código | Quando |
|---|---|
| 200 / 201 | Sucesso / recurso criado |
| 400 | Campo ausente ou inválido |
| 401 | Sem token, token inválido/expirado, ou login incorreto |
| 404 | Recurso não existe (ou é de outro usuário) |
| 409 | Conflito: duplicidade (BR-01) ou transição de sessão inválida |
| 413 | Arquivo maior que `MAX_UPLOAD_MB` (padrão 20 MB) |
| 415 | Arquivo enviado não é PDF (BR-02) |
| 503 | Banco de dados indisponível |

---

## Autenticação (Sprint 1, corrigida)

### `POST /register` — FR-08
Campos: `username`, `email`, `name`, `password` (obrigatórios), `program` (curso de graduação, opcional).
Resposta `201`:
```json
{"status": "success", "user": {"id": 1, "username": "maria_st", "email": "maria@focus.com", "name": "Maria Souza"}}
```
Erros: `400` (validação), `409` (`username already registered`, `email already registered`,
`username and email already registered`).

### `POST /login` — FR-09
Campos: `user` (username **ou** email; também aceita `username` ou `email`) e `password`.
Resposta `200`: `{"status": "success", "access_token": "...", "logged_as": "maria_st"}`.
Se a requisição já tiver um token válido, responde `200` com `logged_as` sem exigir senha.
Erro `401`: `invalid username or password` (mesma mensagem para usuário inexistente e senha errada).

### `GET /health`
`{"status": "ok"}`

---

## Disciplinas (courses) 🔒

Objeto `course`:
```json
{"id": 3, "name": "Cálculo I", "teacher": "Prof. Ana", "created_at": "2026-11-23T14:00:00+00:00", "updated_at": "2026-11-23T14:00:00+00:00"}
```
`name` e `teacher` são obrigatórios (máx. 100 caracteres). Espaços nas pontas e repetidos são removidos.

| Método e rota | Req. | Sucesso | Erros |
|---|---|---|---|
| `GET /courses` | FR-02 | `200` `{"courses": [...]}` em ordem alfabética | — |
| `GET /courses/{id}` | FR-02 | `200` `{"course": {...}}` | 404 |
| `POST /courses` | FR-01, BR-01 | `201` `{"course": {...}}` | 400, 409 |
| `PUT /courses/{id}` | FR-03, BR-01 | `200` `{"course": {...}}` (envie `name` **e** `teacher`) | 400, 404, 409 |
| `DELETE /courses/{id}` | FR-04 | `200` | 404, 409 se houver sessão em andamento (traz `session_id`) |

**BR-01:** o mesmo usuário não pode ter duas disciplinas com o mesmo `name` + `teacher`,
sem diferenciar maiúsculas/minúsculas nem espaços extras (`"cálculo  i"` / `"PROF. ANA"`
conflita com `"Cálculo I"` / `"Prof. Ana"`). Mesmo nome com outro professor é permitido,
e usuários diferentes podem ter disciplinas iguais.

**Exclusão:** apaga também os PDFs (banco e disco) e o histórico de sessões da disciplina.

### `POST /courses/{id}/pdf` 🔒 — FR-05, BR-02
`multipart/form-data` com o arquivo no campo **`file`**.

```bash
curl -H "Authorization: Bearer $TOKEN" -F "file=@apostila.pdf;type=application/pdf" \
     http://localhost:8080/api/courses/3/pdf
```
Resposta `201`:
```json
{"status": "success", "pdf": {"id": 1, "course_id": 3, "original_name": "apostila.pdf", "size_bytes": 48211, "mime": "application/pdf", "created_at": "..."}}
```
**BR-02:** o servidor exige as duas coisas: Content-Type declarado `application/pdf`
**e** conteúdo que seja de fato um PDF (assinatura `%PDF-` no início e `%%EOF` no fim).
Um `.txt` renomeado ou uma imagem com tipo forjado recebe `415`.
Outros erros: `400` (campo ausente / arquivo vazio), `404`, `413`.

---

## Sessões de foco (sessions) 🔒

O cliente **nunca** envia horários. Início, fim e pausas são registrados com o relógio
do servidor, em UTC (BR-03); campos como `started_at` ou `ended_at` enviados pelo cliente são ignorados.

### `POST /sessions` — FR-06

| `action` | Campos | Estado exigido | Novo estado | Sucesso |
|---|---|---|---|---|
| `start` | `course_id` | nenhuma sessão aberta do usuário | `in_progress` | `201` |
| `pause` | `session_id` | `in_progress` | `paused` | `200` |
| `resume` | `session_id` | `paused` | `in_progress` | `200` |
| `finish` | `session_id` | `in_progress` ou `paused` | `finished` | `200` |

Ação fora de ordem responde `409`. Cada usuário tem no máximo uma sessão aberta;
tentar iniciar outra responde `409` com o `session_id` da que está aberta.
Finalizar uma sessão pausada encerra a pausa no mesmo instante.

Exemplo de um Pomodoro: `start` → 25 min → `pause` → 5 min → `resume` → 25 min → `finish`:
```json
{
  "status": "success",
  "session": {
    "id": 7, "course_id": 3, "status": "finished",
    "started_at": "2026-11-23T14:00:00+00:00", "ended_at": "2026-11-23T14:55:00+00:00",
    "total_duration_seconds": 3300,
    "paused_seconds": 300,
    "effective_seconds": 3000,
    "pauses": [{"started_at": "2026-11-23T14:25:00+00:00", "ended_at": "2026-11-23T14:30:00+00:00"}]
  }
}
```
**BR-04:** `effective_seconds = total_duration_seconds − paused_seconds`.
Em sessão ainda aberta os tempos são calculados até o momento da consulta,
para o frontend poder mostrar o cronômetro.

### `GET /sessions?course={id}` — FR-07
O filtro `course` é opcional; sem ele, lista as sessões de todas as disciplinas.
Ordem: mais recente primeiro.
```json
{
  "status": "success",
  "sessions": [ { "...": "mesmo formato acima" } ],
  "summary": {"session_count": 3, "finished_sessions": 2, "total_effective_seconds": 4500}
}
```
`total_effective_seconds` soma apenas as sessões finalizadas.
Erros: `400` (filtro não é inteiro positivo), `404` (disciplina não existe ou é de outro usuário).
