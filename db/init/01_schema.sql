-- Runs once, when the db volume is empty.
-- Columns match the fields used by backend/api_blueprint/api.py.
CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    username     VARCHAR(20)  NOT NULL UNIQUE,
    email        VARCHAR(100) NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    password     VARCHAR(255) NOT NULL,
    data_criacao TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
