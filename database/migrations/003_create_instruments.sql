-- ============================================================
-- Migration 003: Create instruments table
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- ============================================================

-- Enable trigram extension for full-text search on instrument names
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Instrument types supported by the system
CREATE TYPE instrument_type_enum AS ENUM ('equity', 'bond', 'etf', 'fund', 'index');

CREATE TABLE instruments (
    id          UUID                    NOT NULL DEFAULT gen_random_uuid(),
    symbol      VARCHAR(50)             NOT NULL,   -- e.g. AAPL, MSFT
    isin        CHAR(12)                NULL,       -- International identifier
    cusip       CHAR(9)                 NULL,       -- US identifier
    sedol       CHAR(7)                 NULL,       -- UK identifier
    name        VARCHAR(255)            NOT NULL,   -- e.g. "Apple Inc."
    type        instrument_type_enum    NOT NULL,
    currency    CHAR(3)                 NOT NULL,   -- ISO 4217 e.g. USD
    sector      VARCHAR(100)            NULL,       -- e.g. Technology, Finance
    exchange    VARCHAR(50)             NULL,       -- e.g. NASDAQ, NYSE
    country     CHAR(2)                 NULL,       -- ISO 3166 e.g. US, FR
    is_active   BOOLEAN                 NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ             NOT NULL DEFAULT NOW(),

    CONSTRAINT instruments_pkey       PRIMARY KEY (id),
    CONSTRAINT instruments_symbol_key UNIQUE (symbol),
    CONSTRAINT instruments_isin_key   UNIQUE (isin),
    CONSTRAINT instruments_cusip_key  UNIQUE (cusip),
    CONSTRAINT instruments_sedol_key  UNIQUE (sedol)
);

-- Indexes
CREATE INDEX idx_instruments_type   ON instruments (type);
CREATE INDEX idx_instruments_sector ON instruments (sector);
CREATE INDEX idx_instruments_search ON instruments USING GIN (name gin_trgm_ops);  -- full-text search

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 003_create_instruments.sql
-- ============================================================
