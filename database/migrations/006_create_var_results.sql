-- ============================================================
-- Migration 006: Create var_results table
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- Depends: 002_create_portfolios.sql
-- ============================================================

-- Each row = one VaR calculation run for a portfolio
-- This is the main output table of the Monte Carlo engine

CREATE TABLE var_results (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    portfolio_id        UUID            NOT NULL,
    var_95              DECIMAL(18,6)   NOT NULL,   -- Value at Risk at 95% confidence (e.g. 0.05 = 5% loss)
    var_99              DECIMAL(18,6)   NOT NULL,   -- Value at Risk at 99% confidence (stricter)
    cvar_95             DECIMAL(18,6)   NULL,       -- Conditional VaR (expected loss beyond var_95)
    cvar_99             DECIMAL(18,6)   NULL,       -- Conditional VaR at 99%
    portfolio_value     DECIMAL(18,2)   NOT NULL,   -- total portfolio value at time of calculation
    num_simulations     INTEGER         NOT NULL DEFAULT 10000,  -- how many Monte Carlo paths were run
    time_horizon_days   INTEGER         NOT NULL DEFAULT 10,     -- forecast window in days
    historical_window   INTEGER         NOT NULL DEFAULT 252,    -- lookback period (252 = 1 trading year)
    calculation_time_ms INTEGER         NULL,       -- how long the calculation took (for performance monitoring)
    calculated_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),  -- when this result was produced

    CONSTRAINT var_results_pkey      PRIMARY KEY (id),
    CONSTRAINT var_results_port_fk   FOREIGN KEY (portfolio_id)
        REFERENCES portfolios (id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_var_portfolio     ON var_results (portfolio_id);
CREATE INDEX idx_var_calculated_at ON var_results (calculated_at DESC);
CREATE INDEX idx_var_port_time     ON var_results (portfolio_id, calculated_at DESC);

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 006_create_var_results.sql
-- ============================================================
