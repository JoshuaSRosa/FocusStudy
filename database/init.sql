-- =====================================================================
-- FocusStudy - PostgreSQL 16 schema
--
-- The postgres image entrypoint runs this script automatically INSIDE the
-- database defined by POSTGRES_DB, and only when the data volume is empty.
-- That is why there is no CREATE DATABASE / USE here (USE does not exist
-- in PostgreSQL and IDENTITY(1,1) is SQL Server syntax).
--
-- To recreate the database from scratch:  docker compose down -v && docker compose up
-- =====================================================================

-- ---------------------------------------------------------------------
-- Users (Sprint 1, fixed)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id             SERIAL       PRIMARY KEY,
    username       VARCHAR(20)  NOT NULL,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(100) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    program        VARCHAR(100),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Case-insensitive uniqueness
CREATE UNIQUE INDEX ux_users_username ON users (LOWER(username));
CREATE UNIQUE INDEX ux_users_email    ON users (LOWER(email));

-- ---------------------------------------------------------------------
-- Courses (FR-01..FR-04)
-- ---------------------------------------------------------------------
CREATE TABLE courses (
    id          SERIAL       PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL CHECK (BTRIM(name) <> ''),
    teacher     VARCHAR(100) NOT NULL CHECK (BTRIM(teacher) <> ''),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- BR-01: the same user cannot have two courses with the same
-- name + teacher. The API checks before inserting; the index is the
-- final guarantee against race conditions.
CREATE UNIQUE INDEX ux_courses_user_name_teacher
    ON courses (user_id, LOWER(name), LOWER(teacher));

-- ---------------------------------------------------------------------
-- Course PDFs (FR-05 / BR-02)
-- The file lives on disk (UPLOAD_DIR volume); only metadata is stored here.
-- ---------------------------------------------------------------------
CREATE TABLE pdfs (
    id             SERIAL       PRIMARY KEY,
    course_id      INT          NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    original_name  VARCHAR(255) NOT NULL,
    stored_name    VARCHAR(64)  NOT NULL UNIQUE,
    size_bytes     INT          NOT NULL CHECK (size_bytes > 0),
    mime           VARCHAR(50)  NOT NULL DEFAULT 'application/pdf'
                                CHECK (mime = 'application/pdf'),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_pdfs_course ON pdfs (course_id);

-- ---------------------------------------------------------------------
-- Focus sessions / Pomodoro (FR-06, FR-07, BR-03, BR-04)
-- started_at/ended_at are ALWAYS written with the server clock.
-- ---------------------------------------------------------------------
CREATE TABLE sessions (
    id                 SERIAL      PRIMARY KEY,
    user_id            INT         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id          INT         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    status             VARCHAR(15) NOT NULL DEFAULT 'in_progress'
                                   CHECK (status IN ('in_progress', 'paused', 'finished')),
    started_at         TIMESTAMPTZ NOT NULL,
    ended_at           TIMESTAMPTZ,
    effective_seconds  INT         CHECK (effective_seconds IS NULL OR effective_seconds >= 0),
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    CHECK ((status = 'finished') = (ended_at IS NOT NULL))
);

-- At most ONE open session (in progress or paused) per user
CREATE UNIQUE INDEX ux_sessions_open_per_user ON sessions (user_id) WHERE ended_at IS NULL;
CREATE INDEX ix_sessions_user_course ON sessions (user_id, course_id, started_at DESC);

CREATE TABLE pauses (
    id          SERIAL      PRIMARY KEY,
    session_id  INT         NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- At most ONE open pause per session
CREATE UNIQUE INDEX ux_pauses_open_per_session ON pauses (session_id) WHERE ended_at IS NULL;
CREATE INDEX ix_pauses_session ON pauses (session_id);
