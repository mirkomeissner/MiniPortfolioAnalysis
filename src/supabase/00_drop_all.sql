-- --- 1. DROP VIEWS ---
-- Views müssen vor den Tabellen gelöscht werden, auf die sie referenzieren.
DROP VIEW IF EXISTS public.asset_static_data;
DROP VIEW IF EXISTS public.ref_transaction_type;
DROP VIEW IF EXISTS shared.users;

-- --- 2. DROP PUBLIC TABLES (User Data) ---
-- Diese Tabellen hängen von den Stammdaten in 'shared' und 'public.users' ab.
DROP TABLE IF EXISTS public.daily_holdings;
DROP TABLE IF EXISTS public.user_import_settings;
DROP TABLE IF EXISTS public.transactions;
DROP TABLE IF EXISTS public.accounts;
DROP TABLE IF EXISTS public.user_secrets;

-- --- 3. DROP SHARED TABLES (Global Data) ---
-- Zuerst Tabellen mit Foreign Keys auf andere Shared-Tabellen.
DROP TABLE IF EXISTS shared.exchange_rates;
DROP TABLE IF EXISTS shared.asset_prices;
DROP TABLE IF EXISTS shared.country_region_mapping;
DROP TABLE IF EXISTS shared.asset_static_data;
DROP TABLE IF EXISTS shared.ref_transaction_logic;

-- Jetzt die reinen Referenz-Tabellen (Lookup-Tabellen).
DROP TABLE IF EXISTS shared.ref_currencies;
DROP TABLE IF EXISTS shared.ref_transaction_type;
DROP TABLE IF EXISTS shared.ref_instrument_type;
DROP TABLE IF EXISTS shared.ref_price_source;
DROP TABLE IF EXISTS shared.ref_sector;
DROP TABLE IF EXISTS shared.ref_region;
DROP TABLE IF EXISTS shared.ref_asset_class;

-- --- 4. DROP BASE TABLES ---
-- Zuletzt die zentrale User-Tabelle.
DROP TABLE IF EXISTS public.users;

-- --- 5. CLEANUP SCHEMAS (Optional) ---
-- Falls du die Schemata komplett entfernen willst, entkommentiere die nächsten Zeilen.
DROP SCHEMA IF EXISTS shared CASCADE;
-- DROP SCHEMA IF EXISTS public CASCADE;

