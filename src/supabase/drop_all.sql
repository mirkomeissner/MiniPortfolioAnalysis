-- ==========================================
-- RESET SCRIPT: drop all tables
-- ==========================================

DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS asset_static_data CASCADE;

DROP TABLE IF EXISTS accounts CASCADE;

DROP TABLE IF EXISTS ref_type CASCADE;
DROP TABLE IF EXISTS ref_asset_class CASCADE;
DROP TABLE IF EXISTS ref_region CASCADE;
DROP TABLE IF EXISTS ref_sector CASCADE;
DROP TABLE IF EXISTS ref_price_source CASCADE;

