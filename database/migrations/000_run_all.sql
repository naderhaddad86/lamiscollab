-- ============================================================
-- Migration 000: Master runner — creates database and runs all migrations
-- Project: VaR Monte Carlo Enhancement System
-- Author:  Lamis Zitouni
-- Date:    2026-02
--
-- HOW TO USE (run this ONE command in your terminal):
--
--   psql -h localhost -U postgres -f 000_run_all.sql
--
-- That's it. All 6 tables will be created in the right order.
-- ============================================================

-- 1. Create the database (skip if it already exists)
SELECT 'CREATE DATABASE var_db'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'var_db'
)\gexec

-- 2. Connect to var_db for everything below
\c var_db

-- 3. Run each migration in order
\i 001_create_users.sql
\i 002_create_portfolios.sql
\i 003_create_instruments.sql
\i 004_create_positions.sql
\i 005_create_price_history.sql
\i 006_create_var_results.sql

-- 4. Confirm all tables were created
\echo ''
\echo '===== Tables created successfully ====='
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
