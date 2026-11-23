# FocusStudy

API do FocusStudy: disciplinas, materiais em PDF e sessões de foco (Pomodoro) com cálculo
do tempo efetivo de estudo.

Todo o código, o banco e a API usam nomenclatura em inglês (`courses`, `sessions`, `name`,
`teacher`...); a documentação do processo está em português.

Stack: Python 3.12, Flask 3, Flask-JWT-Extended, PostgreSQL 16, gunicorn, Docker Compose.

## Como rodar

```bash
cp .env.example .env          # troque JWT_SECRET_KEY e a senha do banco
docker compose up --build
curl http://localhost:8080/api/health   # {"status":"ok"}
```

O `database/init.sql` só roda quando o volume do banco está vazio. Depois de mudar o
schema (ao atualizar do Sprint 1 ou da versão com nomes em português), recrie o banco. **Isso apaga os dados:**

```bash
docker compose down -v && docker compose up --build
```

Para rodar sem Docker, veja `backend/instructions.txt`.

## Como testar

```bash
docker compose --profile test run --rm tests
```

O comando sobe o Postgres, cria um banco separado (`focusstudy_test`), roda os testes e
imprime a cobertura e a matriz de rastreabilidade. O banco real não é tocado.

## Estrutura

```
database/
  init.sql                 schema PostgreSQL
backend/
  main.py                  app factory (gunicorn: main:create_app())
  database.py              pool de conexões + transaction()
  clock.py                 relógio do servidor (BR-03)
  focus.py                 cálculo do tempo efetivo (BR-04)
  validations.py           validações de entrada e de PDF (BR-02)
  api_blueprint/
    api.py                 blueprint /api e utilitários
    auth.py                /health, /register, /login
    courses.py             /courses e upload de PDF
    sessions.py            /sessions
  tests/                   pytest (unidade, endpoint, aceitação)
    requirements_catalog.py  catálogo dos IDs de requisito (FR, BR, NFR, VAL)
docs/
  API.md                   referência dos endpoints
  requisitos-sprint2.md    requisitos, critérios (GRE2) e matriz de rastreabilidade
  pdca-sprint2.md          ciclo PDCA, verificação e defeitos corrigidos
  validacao-sprint2.md     validação com a equipe e termo de aceite
  sprint2-gpr3.md          Sprint 2: backlog, DoD e incremento (GPR3)
```
