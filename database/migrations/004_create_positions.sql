-- ============================================================
-- Migration 004: Create positions table
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- Depends: 002_create_portfolios.sql, 003_create_instruments.sql
-- ============================================================

CREATE TABLE positions (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    portfolio_id        UUID            NOT NULL,   -- which portfolio holds this
    instrument_id       UUID            NOT NULL,   -- which instrument is held
    quantity            DECIMAL(18,6)   NOT NULL,   -- number of units (e.g. 150.5 shares)
    avg_purchase_price  DECIMAL(18,6)   NOT NULL,   -- average cost basis per unit
    current_price       DECIMAL(18,6)   NULL,       -- latest market price (updated by market data service)
    market_value        DECIMAL(18,2)   NULL,       -- quantity * current_price
    unrealized_pnl      DECIMAL(18,2)   NULL,       -- market_value - (quantity * avg_purchase_price)
    purchase_date       DATE            NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT positions_pkey          PRIMARY KEY (id),
    CONSTRAINT positions_portfolio_fk  FOREIGN KEY (portfolio_id)
        REFERENCES portfolios (id) ON DELETE CASCADE,
    CONSTRAINT positions_instrument_fk FOREIGN KEY (instrument_id)
        REFERENCES instruments (id) ON DELETE RESTRICT,  -- can't delete instrument if in use
    CONSTRAINT uq_positions_port_inst  UNIQUE (portfolio_id, instrument_id)  -- one row per instrument per portfolio
);

-- Indexes
CREATE INDEX idx_positions_portfolio   ON positions (portfolio_id);
CREATE INDEX idx_positions_instrument  ON positions (instrument_id);

-- Auto-update updated_at
CREATE TRIGGER positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 004_create_positions.sql
-- ============================================================
