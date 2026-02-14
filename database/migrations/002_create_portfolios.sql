-- ============================================================
-- Migration 002: Create portfolios table
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- Depends: 001_create_users.sql
-- ============================================================

CREATE TABLE portfolios (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL,           -- which user owns this portfolio
    name            VARCHAR(255)    NOT NULL,
    description     TEXT            NULL,
    base_currency   CHAR(3)         NOT NULL DEFAULT 'USD',  -- ISO 4217 e.g. USD, EUR
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT portfolios_pkey    PRIMARY KEY (id),
    CONSTRAINT portfolios_user_fk FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_portfolios_user_id     ON portfolios (user_id);
CREATE INDEX idx_portfolios_user_active ON portfolios (user_id, is_active);

-- Auto-update updated_at
CREATE TRIGGER portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 002_create_portfolios.sql
-- ============================================================
