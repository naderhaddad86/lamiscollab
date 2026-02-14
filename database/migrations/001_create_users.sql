-- ============================================================
-- Migration 001: Create users table
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- ============================================================

-- Enable UUID generation (required for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Role enum: controls what each user can do in the system
CREATE TYPE user_role_enum AS ENUM ('admin', 'analyst', 'viewer');

CREATE TABLE users (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    email           VARCHAR(255)    NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,           -- bcrypt hash, never plain text
    first_name      VARCHAR(100)    NULL,
    last_name       VARCHAR(100)    NULL,
    role            user_role_enum  NOT NULL DEFAULT 'analyst',
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ     NULL,

    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email)
);

-- Indexes
CREATE INDEX idx_users_role   ON users (role);
CREATE INDEX idx_users_active ON users (is_active) WHERE is_active = TRUE;

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 001_create_users.sql
-- ============================================================
