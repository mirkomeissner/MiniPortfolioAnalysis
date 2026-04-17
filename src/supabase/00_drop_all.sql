-- ==========================================
-- RESET SCRIPT: drop all tables
-- ==========================================

-- 1. Drop "child" tables first (those that depend on other tables)
DROP TABLE IF EXISTS daily_holdings CASCADE;
DROP TABLE IF EXISTS asset_prices CASCADE;
DROP TABLE IF EXISTS exchange_rates CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS user_import_settings CASCADE;
DROP TABLE IF EXISTS country_region_mapping CASCADE;

-- 2. Drop "parent" tables
DROP TABLE IF EXISTS asset_static_data CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;

-- 3. Drop reference tables (Lookup tables)
DROP TABLE IF EXISTS ref_transaction_type CASCADE;
DROP TABLE IF EXISTS ref_asset_class CASCADE;
DROP TABLE IF EXISTS ref_region CASCADE;
DROP TABLE IF EXISTS ref_sector CASCADE;
DROP TABLE IF EXISTS ref_price_source CASCADE;
DROP TABLE IF EXISTS ref_instrument_type CASCADE;

-- Optional: Reset functions or views if you created any
-- DROP VIEW IF EXISTS portfolio_valuation_view;
