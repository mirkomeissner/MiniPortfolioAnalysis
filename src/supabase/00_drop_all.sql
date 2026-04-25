-- ==========================================================
-- DROP ALL SCRIPT (Clean Wipe)
-- ==========================================================

-- 1. Drop Views first (they depend on tables)
DROP VIEW IF EXISTS public.daily_holdings CASCADE;
DROP VIEW IF EXISTS public.asset_static_data CASCADE;
DROP VIEW IF EXISTS public.ref_transaction_type CASCADE;
DROP VIEW IF EXISTS shared.users CASCADE;

-- 2. Drop Tables in PUBLIC (User data)
-- We use CASCADE to ensure associated policies and triggers are also removed
DROP TABLE IF EXISTS public.incremental_holdings CASCADE;
DROP TABLE IF EXISTS public.user_import_settings CASCADE;
DROP TABLE IF EXISTS public.transactions CASCADE;
DROP TABLE IF EXISTS public.accounts CASCADE;
DROP TABLE IF EXISTS public.user_secrets CASCADE; -- TO BE REOMVED AFTER REFACTORING
DROP TABLE IF EXISTS public.users CASCADE;

-- 3. Drop Tables in SHARED (Global data)
DROP TABLE IF EXISTS shared.exchange_rates CASCADE;
DROP TABLE IF EXISTS shared.asset_prices CASCADE;
DROP TABLE IF EXISTS shared.country_region_mapping CASCADE;
DROP TABLE IF EXISTS shared.asset_static_data CASCADE;
DROP TABLE IF EXISTS shared.ref_transaction_logic CASCADE;
DROP TABLE IF EXISTS shared.ref_currencies CASCADE;
DROP TABLE IF EXISTS shared.ref_transaction_type CASCADE;
DROP TABLE IF EXISTS shared.ref_instrument_type CASCADE;
DROP TABLE IF EXISTS shared.ref_price_source CASCADE;
DROP TABLE IF EXISTS shared.ref_sector CASCADE;
DROP TABLE IF EXISTS shared.ref_region CASCADE;
DROP TABLE IF EXISTS shared.ref_asset_class CASCADE;

-- 4. Drop Schemas (optional, if you want a total reset)
-- Only use this if you want to remove the namespaces entirely
DROP SCHEMA IF EXISTS shared CASCADE;
-- DROP SCHEMA IF EXISTS public CASCADE;

-- 5. Re-create public schema if it was dropped 
-- (Supabase needs the public schema to exist)
-- CREATE SCHEMA IF NOT EXISTS public;
