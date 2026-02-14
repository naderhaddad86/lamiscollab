-- ============================================================
-- Migration 005: Create price_history table (TimescaleDB hypertable)
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
-- Depends: 003_create_instruments.sql
-- NOTE:    Requires TimescaleDB extension to be installed
-- ============================================================

-- Enable TimescaleDB (must be installed via docker-compose)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE price_history (
    instrument_id   UUID            NOT NULL,       -- which instrument this price belongs to
    timestamp       TIMESTAMPTZ     NOT NULL,       -- exact date/time of price observation
    open            DECIMAL(18,6)   NULL,           -- price at market open
    high            DECIMAL(18,6)   NULL,           -- highest price of the period
    low             DECIMAL(18,6)   NULL,           -- lowest price of the period
    close           DECIMAL(18,6)   NOT NULL,       -- closing price (required - used for VaR calc)
    adj_close       DECIMAL(18,6)   NULL,           -- adjusted for dividends/splits
    volume          BIGINT          NULL,           -- number of shares/units traded
    source          VARCHAR(50)     NOT NULL DEFAULT 'yahoo',  -- data provider name

    CONSTRAINT price_history_pkey      PRIMARY KEY (instrument_id, timestamp),
    CONSTRAINT price_history_inst_fk   FOREIGN KEY (instrument_id)
        REFERENCES instruments (id) ON DELETE CASCADE
);

-- Convert to TimescaleDB hypertable (partitioned by time, 7-day chunks)
-- This makes time-range queries MUCH faster for VaR calculations
SELECT create_hypertable(
    'price_history',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    partitioning_column => 'instrument_id',
    number_partitions   => 4,
    if_not_exists       => TRUE
);

-- Indexes (TimescaleDB automatically indexes the time column)
CREATE INDEX idx_price_time_desc  ON price_history (timestamp DESC);
CREATE INDEX idx_price_inst_time  ON price_history (instrument_id, timestamp DESC);

-- Compression: compress chunks older than 90 days to save disk space
SELECT add_compression_policy('price_history', INTERVAL '90 days');

-- Retention: delete data older than 5 years automatically
SELECT add_retention_policy('price_history', INTERVAL '5 years');

-- ============================================================
-- To run: psql -h localhost -U postgres -d var_db -f 005_create_price_history.sql
-- ============================================================
