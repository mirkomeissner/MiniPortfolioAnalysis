-- --- CLEANUP SCRIPT ---
-- Drop views from shared to public
DROP VIEW IF EXISTS shared.users;

-- Drop tables in public schema
DROP TABLE IF EXISTS public.daily_holdings;
DROP TABLE IF EXISTS public.user_import_settings;
DROP TABLE IF EXISTS public.transactions;
DROP TABLE IF EXISTS public.accounts;
DROP TABLE IF EXISTS public.user_secrets; 
DROP TABLE IF EXISTS public.users;

-- Drop tables in shared schema
DROP TABLE IF EXISTS shared.exchange_rates;
DROP TABLE IF EXISTS shared.asset_prices;
DROP TABLE IF EXISTS shared.country_region_mapping;
DROP TABLE IF EXISTS shared.asset_static_data;
DROP TABLE IF EXISTS shared.ref_transaction_type;
DROP TABLE IF EXISTS shared.ref_currencies;
DROP TABLE IF EXISTS shared.ref_instrument_type;
DROP TABLE IF EXISTS shared.ref_price_source;
DROP TABLE IF EXISTS shared.ref_sector;
DROP TABLE IF EXISTS shared.ref_region;
DROP TABLE IF EXISTS shared.ref_asset_class;

-- Drop schemas
DROP SCHEMA IF EXISTS shared;
-- Usually you don't drop public in Supabase, but for a clean state:
-- DROP SCHEMA IF EXISTS public CASCADE;
