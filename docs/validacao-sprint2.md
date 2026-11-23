# Validação do Sprint 2 (ISO/IEC 12207)

**Validação** responde: *construímos a API certa?* Ou seja, ela atende à necessidade
real da equipe do FocusStudy? A verificação (`docs/pdca-sprint2.md`) mostra que a API
faz o que os requisitos dizem; a validação confirma que esses requisitos resolvem o
problema de quem vai usar.

## Necessidade a validar

> A equipe do FocusStudy precisa que o estudante **registre suas sessões de estudo**
> por disciplina e saiba **quanto tempo realmente estudou**.

História de usuário (VAL-01):
*"Como estudante, quero registrar minhas sessões de estudo de uma disciplina, com
pausas, para saber quanto tempo realmente estudei."*

## Critérios de aceitação

(No código, `test_acceptance.py`, os critérios CA1 a CA6 aparecem como AC1 a AC6.)

| CA | Critério | Requisitos ligados | Evidência automatizada |
|---|---|---|---|
| CA1 | Consigo cadastrar a disciplina que estudo | FR-01, BR-01 | `test_acceptance.py` + `test_courses.py` |
| CA2 | Consigo anexar o material (PDF) da disciplina | FR-05, BR-02 | `test_acceptance.py` + `test_pdf.py` |
| CA3 | Consigo iniciar, pausar, retomar e finalizar um Pomodoro | FR-06, BR-03 | `test_acceptance.py` + `test_sessions.py` |
| CA4 | O tempo mostrado desconta as pausas | BR-04 | `test_acceptance.py` (2 × 25 min com 5 min de pausa = 50 min) |
| CA5 | Vejo o histórico da disciplina com o total estudado | FR-07 | `test_acceptance.py` (`summary.total_effective_seconds`) |
| CA6 | Outro estudante não vê meus dados | NFR-01 | `test_acceptance.py` + testes `NFR-01` |

O teste `test_acceptance.py` executa o fluxo do estudante de ponta a ponta, como o
frontend faria, e **passou**. Isso é evidência de que a necessidade *pode* ser atendida,
mas não substitui a validação: só a equipe pode confirmar que o comportamento é o que
ela queria.

## Como validar com a equipe (Sprint Review)

Roteiro de demonstração, cerca de 10 minutos, com a API rodando via `docker compose up`
e um cliente HTTP (Postman, Insomnia ou o frontend):

1. Cadastrar um estudante e fazer login.
2. Criar a disciplina "Cálculo I / Prof. Ana". Tentar criar "cálculo i / PROF. ANA" e
   mostrar o `409` (BR-01).
3. Anexar um PDF real. Renomear uma imagem para `.pdf`, enviar e mostrar o `415` (BR-02).
4. Iniciar uma sessão, pausar, retomar e finalizar. Mostrar que `started_at`/`ended_at` vieram do
   servidor e que `effective_seconds` desconta a pausa (BR-03, BR-04).
5. Abrir `GET /api/sessions?course={id}` e mostrar o histórico com o total.
6. Logar com outro usuário e mostrar que ele não vê nada do primeiro.

### Ensaio do roteiro (pré-validação)

O roteiro acima foi executado (e repetido após a padronização da nomenclatura em inglês) por HTTP contra a API rodando com **gunicorn** e PostgreSQL 16,
num banco recém-criado pelo `init.sql`:

| Passo | Resultado obtido | OK |
|---|---|---|
| 1 | `/register` → `201`; `/login` → `200` com token | ✔ |
| 2 | "Cálculo I / Prof. Ana" → `201`; "cálculo  i / PROF. ANA" → `409` | ✔ |
| 3 | PDF real → `201`; PNG renomeado para `.pdf` com tipo `application/pdf` → `415` | ✔ |
| 4 | `started_at` enviado pelo cliente (2020) ignorado; sessão real de 6 s com 2 s de pausa → `effective_seconds = 4`; `resume` fora de ordem → `409` | ✔ |
| 5 | Histórico: `{"session_count": 1, "finished_sessions": 1, "total_effective_seconds": 4}` | ✔ |
| 6 | Outro usuário: lista vazia e `404` na disciplina do primeiro; sem token → `401` | ✔ |

Na primeira tentativa de ensaio, o passo 2 falhava com `400` (defeito B-16). Sem a
reverificação, o erro teria aparecido na frente da equipe na Review.

Perguntas para a equipe confirmar (decisões tomadas no detalhamento dos requisitos):

- Excluir uma disciplina deve **apagar** o histórico dela, ou deve ser **bloqueado**
  quando houver histórico?
- Uma sessão por vez por estudante atende ao uso esperado?
- O histórico precisa de filtro por período (semana, mês) já no próximo Sprint?
- O tamanho máximo de PDF de 20 MB é adequado?

## Termo de aceite

Preencher na Sprint Review. Critério não aceito volta para o backlog como ajuste.

| CA | Aceito? (S/N) | Observação da equipe |
|---|---|---|
| CA1 | | |
| CA2 | | |
| CA3 | | |
| CA4 | | |
| CA5 | | |
| CA6 | | |

Data: ____/____/______  Responsável (PO / equipe): ______________________________
