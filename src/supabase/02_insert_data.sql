

INSERT INTO shared.ref_asset_class (code, label)
VALUES 
  ('LIQ', 'Liquidity'),
  ('BON', 'Bonds & Bond Funds'),
  ('EQU', 'Equities & Equity Funds'),
  ('ALT', 'Alternative Investments')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_region (code, label)
VALUES 
  ('GLO',  'Global / World'),
  ('DEV',  'Developed Markets'),
  ('USA',  'United States'),
  ('NAM',  'North America (Ex-USA)'),
  ('EUR',  'Europe'),
  ('UK',   'United Kingdom'),
  ('APAC', 'Asia Pacific'),
  ('EM',   'Emerging Markets'),
  ('MEAF', 'Middle East & Africa'),
  ('LATM', 'Latin America')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_sector (code, label)
VALUES 
  ('10', 'Energy'), ('15', 'Materials'), ('20', 'Industrials'),
  ('25', 'Consumer Discretionary'), ('30', 'Consumer Staples'),
  ('35', 'Health Care'), ('40', 'Financials'), ('45', 'Information Technology'),
  ('50', 'Communication Services'), ('55', 'Utilities'), ('60', 'Real Estate')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_price_source (code, label)
VALUES 
  ('YFN', 'YFINANCE'),
  ('GFN', 'GOOGLEFINANCE'),
  ('ARV', 'ARIVA'),
  ('TGO', 'TIINGO'),
  ('MKS', 'MARKETSTACK'),
  ('EODHD', 'EOD HISTORICAL DATA')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_instrument_type (code, label)
VALUES 
  ('STO', 'Stock'),
  ('BON', 'Bond'),
  ('FUN', 'Fund'),
  ('ETF', 'ETF'),
  ('CER', 'Certificate')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_transaction_type (code, label)
VALUES 
  ('B', 'Buy'), 
  ('S', 'Sell'), 
  ('TRFIN', 'Transfer-In'), 
  ('TRFOUT', 'Transfer-Out'), 
  ('SPLIT', 'Split')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;

INSERT INTO shared.ref_transaction_logic (transaction_type_code, quantity_sign, amount_sign) VALUES
('B',       1, -1),  -- Qty pos, Amount neg
('S',      -1,  1),  -- Qty neg, Amount pos
('TRFIN',   1,  0),  -- Qty pos, Amount NULL
('TRFOUT', -1,  0),  -- Qty neg, Amount NULL
('SPLIT', NULL, 0)   -- Qty AS IS, Amount NULL
ON CONFLICT (transaction_type_code) DO UPDATE 
SET quantity_sign = EXCLUDED.quantity_sign, 
    amount_sign = EXCLUDED.amount_sign;


insert into shared.ref_currencies (code, label)
values 
-- G10 Currencies (Most Traded)
  ('USD', 'US Dollar'),
  ('EUR', 'Euro'),
  ('JPY', 'Japanese Yen'),
  ('GBP', 'British Pound'),
  ('GBX', 'Pence Sterling'), -- British minor unit (1/100 of GBP), often used in stock markets
  ('CHF', 'Swiss Franc'),
  ('AUD', 'Australian Dollar'),
  ('CAD', 'Canadian Dollar'),
  ('NZD', 'New Zealand Dollar'),
  ('SEK', 'Swedish Krona'),
  ('NOK', 'Norwegian Krone'),

  -- European Currencies
  ('DKK', 'Danish Krone'),
  ('PLN', 'Polish Zloty'),
  ('CZK', 'Czech Koruna'),
  ('HUF', 'Hungarian Forint'),
  ('RON', 'Romanian Leu'),
  ('BGN', 'Bulgarian Lev'),
  ('ISK', 'Icelandic Krona'),

  -- Asian & Pacific Currencies
  ('CNY', 'Chinese Yuan'),
  ('HKD', 'Hong Kong Dollar'),
  ('SGD', 'Singapore Dollar'),
  ('KRW', 'South Korean Won'),
  ('INR', 'Indian Rupee'),
  ('THB', 'Thai Baht'),
  ('IDR', 'Indonesian Rupiah'),
  ('MYR', 'Malaysian Ringgit'),
  ('PHP', 'Philippine Peso'),
  ('TWD', 'New Taiwan Dollar'),
  ('VND', 'Vietnamese Dong'),
  ('LKR', 'Sri Lankan Rupee'),
  ('PKR', 'Pakistani Rupee'),

  -- Middle East & Africa
  ('ILS', 'Israeli New Shekel'),
  ('ILA', 'Israeli Agorot'), -- Israeli minor unit (1/100 of ILS), used in some contexts
  ('TRY', 'Turkish Lira'),
  ('AED', 'UAE Dirham'),
  ('SAR', 'Saudi Riyal'),
  ('QAR', 'Qatari Rial'),
  ('ZAR', 'South African Rand'),
  ('EGP', 'Egyptian Pound'),
  ('BWP', 'Botswana Pula'),
  ('ZMW', 'Zambian Kwacha'),
  ('KES', 'Kenyan Shilling'),
  ('MUR', 'Mauritian Rupee'),
  ('RWF', 'Rwanda Franc'),
  ('TZS', 'Tanzanian Shilling'),
  ('UGX', 'Ugandan Shilling'),
  ('GHS', 'Ghanaian Cedi'),
  ('NGN', 'Nigerian Naira'),
  ('ZWL', 'Zimbabwean Dollar'),
  ('MWK', 'Malawian Kwacha'),
  ('MAD', 'Moroccan Dirham'),

  -- Americas
  ('MXN', 'Mexican Peso'),
  ('BRL', 'Brazilian Real'),
  ('ARS', 'Argentine Peso'),
  ('CLP', 'Chilean Peso'),
  ('COP', 'Colombian Peso'),
  ('PEN', 'Peruvian Sol'),

  -- Others / Commodities
  ('XAU', 'Gold (Troy Ounce)'),
  ('XAG', 'Silver (Troy Ounce)'),
  ('XPT', 'Platinum (Troy Ounce)')
on conflict (code) do update set label = EXCLUDED.label;


INSERT INTO shared.country_region_mapping (country, region_code) VALUES
    ('United States', 'USA'),
    ('Canada', 'NAM'),
    ('Bermuda', 'NAM'),
    ('United Kingdom', 'UK'),
    ('Jersey', 'UK'),
    ('Guernsey', 'UK'),
    ('Isle of Man', 'UK'),
    ('Germany', 'EUR'),
    ('France', 'EUR'),
    ('Italy', 'EUR'),
    ('Spain', 'EUR'),
    ('Netherlands', 'EUR'),
    ('Switzerland', 'EUR'),
    ('Belgium', 'EUR'),
    ('Austria', 'EUR'),
    ('Ireland', 'EUR'),
    ('Sweden', 'EUR'),
    ('Norway', 'EUR'),
    ('Denmark', 'EUR'),
    ('Finland', 'EUR'),
    ('Portugal', 'EUR'),
    ('Luxembourg', 'EUR'),
    ('Japan', 'APAC'),
    ('Australia', 'APAC'),
    ('Singapore', 'APAC'),
    ('New Zealand', 'APAC'),
    ('Hong Kong', 'APAC'),
    ('China', 'EM'),
    ('India', 'EM'),
    ('Taiwan', 'EM'),
    ('South Korea', 'EM'),
    ('Indonesia', 'EM'),
    ('Thailand', 'EM'),
    ('Malaysia', 'EM'),
    ('Philippines', 'EM'),
    ('Vietnam', 'EM'),
    ('Russia', 'EM'),
    ('Poland', 'EM'),
    ('Turkey', 'EM'),
    ('Czech Republic', 'EM'),
    ('Hungary', 'EM'),
    ('Greece', 'EM'),
    ('Brazil', 'LATM'),
    ('Mexico', 'LATM'),
    ('Chile', 'LATM'),
    ('Colombia', 'LATM'),
    ('Peru', 'LATM'),
    ('Argentina', 'LATM'),
    ('South Africa', 'MEAF'),
    ('Israel', 'MEAF'),
    ('Saudi Arabia', 'MEAF'),
    ('United Arab Emirates', 'MEAF'),
    ('Qatar', 'MEAF'),
    ('Kuwait', 'MEAF'),
    ('Egypt', 'MEAF'),
    ('Nigeria', 'MEAF')
ON CONFLICT (country) DO UPDATE SET region_code = EXCLUDED.region_code;



------------------
-- Ticker Data ---
------------------


-- EODHD

CREATE EXTENSION IF NOT EXISTS http;

-- update via:
-- https://eodhd.com/api/exchanges-list/?api_token=MY_TOKEN&fmt=json
WITH file_fetch AS (
    -- 1. Download the JSON file dynamically from the current Supabase Storage Bucket
    SELECT content::jsonb AS json_content
    FROM http_get(
        format('https://%s.supabase.co/storage/v1/object/public/imports/eodhd_exchanges.json', 
               get_supabase_id())
    )
)
-- 2. Insert into your shared table using the fetched JSON content
INSERT INTO shared.ref_exchange (
    code, 
    price_source_code, 
    name, 
    operating_mic, 
    country, 
    currency, 
    country_iso2, 
    country_iso3
)
SELECT 
    t."Code",
    'EODHD' AS price_source_code, -- Explicitly tracking the source
    t."Name",
    NULLIF(t."OperatingMIC", ''),
    t."Country",
    CASE 
        WHEN LENGTH(TRIM(t."Currency")) = 3 THEN TRIM(t."Currency")
        ELSE NULL 
    END AS currency,
    NULLIF(t."CountryISO2", ''),
    NULLIF(t."CountryISO3", '')
FROM file_fetch,
LATERAL jsonb_to_recordset(file_fetch.json_content) AS t(
    "Code" TEXT, 
    "Name" TEXT, 
    "OperatingMIC" TEXT, 
    "Country" TEXT, 
    "Currency" TEXT, 
    "CountryISO2" TEXT, 
    "CountryISO3" TEXT
)
ON CONFLICT (code, price_source_code) 
DO UPDATE SET 
    name = EXCLUDED.name,
    operating_mic = EXCLUDED.operating_mic,
    country = EXCLUDED.country,
    currency = EXCLUDED.currency,
    country_iso2 = EXCLUDED.country_iso2,
    country_iso3 = EXCLUDED.country_iso3;







-- update via:
-- https://eodhd.com/api/exchange-symbol-list/US?api_token=MY_TOKEN&fmt=json
DO $$
DECLARE
    -- Liste hier ALLE deine hochgeladenen JSON-Dateien auf
    file_list TEXT[] := ARRAY[
        'eodhd_US.json', 
        'eodhd_XETRA.json', 
        'eodhd_F.json', 
        'eodhd_PA.json', 
        'eodhd_AS.json', 
        'eodhd_LSE.json', 
        'eodhd_SW.json',
        'eodhd_CO.json', 
        'eodhd_ST.json', 
        'eodhd_OL.json', 
        'eodhd_MC.json', 
        'eodhd_TA.json', 
        'eodhd_WAR.json'
        -- hier bei Bedarf weitere Dateien anhängen
    ];
    current_file TEXT;
    dynamic_url TEXT;
    json_data JSONB;
BEGIN
    FOREACH current_file IN ARRAY file_list LOOP
        
        dynamic_url := format(
            'https://%s.supabase.co/storage/v1/object/public/imports/%s', 
            get_supabase_id(), 
            current_file
        );
        
        RAISE NOTICE 'Starte Import für Datei: %', current_file;

        BEGIN
            SELECT content::jsonb INTO json_data FROM http_get(dynamic_url);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Fehler beim Laden der Datei %: %', current_file, SQLERRM;
            CONTINUE; 
        END;

        -- =========================================================================
        -- SCHRITT 1: Fehlende Börsenplätze "on-the-fly" anlegen (Smart Update)
        -- Jetzt mit automatischer ISO-Erkennung und Namens-Mapping für US-Märkte
        -- =========================================================================
        INSERT INTO shared.ref_exchange (
            code, 
            price_source_code, 
            name, 
            country, 
            currency,
            country_iso2,
            country_iso3
        )
        SELECT DISTINCT 
            t."Exchange",
            'EODHD' AS price_source_code,
            -- Bekannte US-Märkte direkt richtig benennen, ansonsten Fallback auf "Auto-Generated"
            CASE 
                WHEN t."Exchange" = 'NASDAQ'    THEN 'NASDAQ Stock Market'
                WHEN t."Exchange" = 'NYSE'      THEN 'New York Stock Exchange'
                WHEN t."Exchange" = 'PINK'      THEN 'OTC Markets (Pink Sheets)'
                WHEN t."Exchange" = 'AMEX'      THEN 'NYSE American (AMEX)'
                WHEN t."Exchange" = 'NYSE ARCA' THEN 'NYSE Arca'
                WHEN t."Exchange" = 'BATS'      THEN 'Cboe BZX Options Exchange (BATS)'
                ELSE 'Auto-Generated (' || t."Exchange" || ')'
            END AS name,
            t."Country",
            -- Währungs-Absicherung
            CASE 
                WHEN LENGTH(TRIM(t."Currency")) = 3 THEN TRIM(t."Currency")
                ELSE NULL 
            END AS currency,
            -- ISO-Codes automatisch setzen, wenn es ein US-Marktplatz ist
            CASE WHEN t."Country" = 'USA' THEN 'US' ELSE NULL END AS country_iso2,
            CASE WHEN t."Country" = 'USA' THEN 'USA' ELSE NULL END AS country_iso3
        FROM jsonb_to_recordset(json_data) AS t("Exchange" TEXT, "Country" TEXT, "Currency" TEXT)
        WHERE t."Exchange" IS NOT NULL AND t."Exchange" != ''
        ON CONFLICT (code, price_source_code) DO NOTHING;

        -- =========================================================================
        -- SCHRITT 2: Ticker importieren (Jetzt garantiert ohne Foreign-Key-Fehler!)
        -- =========================================================================
        INSERT INTO shared.exchange_tickers (
            ticker_code, 
            exchange_code, 
            price_source_code, 
            name, 
            country, 
            currency, 
            type, 
            isin, 
            is_active, 
            updated_at
        )
        SELECT 
            t."Code",
            t."Exchange",
            'EODHD' AS price_source_code,
            t."Name",
            t."Country",
            CASE 
                WHEN LENGTH(TRIM(t."Currency")) = 3 THEN TRIM(t."Currency")
                ELSE NULL 
            END AS currency,
            t."Type",
            NULLIF(t."Isin", ''),
            TRUE AS is_active,
            NOW() AS updated_at
        FROM jsonb_to_recordset(json_data) AS t(
            "Code" TEXT, "Exchange" TEXT, "Name" TEXT, "Country" TEXT, "Currency" TEXT, "Type" TEXT, "Isin" TEXT
        )
        ON CONFLICT (ticker_code, exchange_code, price_source_code) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            country = EXCLUDED.country,
            currency = EXCLUDED.currency,
            type = EXCLUDED.type,
            isin = EXCLUDED.isin,
            is_active = EXCLUDED.is_active,
            updated_at = NOW();

        RAISE NOTICE 'Datei % erfolgreich importiert.', current_file;
    END LOOP;
END $$;



-- Tiingo

DO $$
DECLARE
    dynamic_url TEXT;
    csv_data TEXT;
BEGIN
    -- 1. URL zur unkomprimierten CSV im Storage zusammenbauen
    dynamic_url := format(
        'https://%s.supabase.co/storage/v1/object/public/imports/supported_tickers.csv', 
        get_supabase_id()
    );
    
    RAISE NOTICE 'Lade Tiingo CSV herunter...';
    SELECT content INTO csv_data FROM http_get(dynamic_url);
    
    -- Temporäre Tabelle für das schnelle Parsen erstellen
    CREATE TEMP TABLE IF NOT EXISTS temp_tiingo (
        line TEXT
    ) ON COMMIT DROP;

    -- Gesamte CSV hocheffizient in Zeilen splitten und in Temp-Tabelle laden
    INSERT INTO temp_tiingo
    SELECT unnest(string_to_array(csv_data, chr(10)));

    -- Header und leere Zeilen entfernen
    DELETE FROM temp_tiingo WHERE line LIKE 'ticker,exchange%' OR line = '' OR line IS NULL;

    -- =========================================================================
    -- SCHRITT 1: Fehlende Exchanges on-the-fly anlegen (Duplikat-sicher dank DISTINCT)
    -- =========================================================================
    INSERT INTO shared.ref_exchange (code, price_source_code, name, country, currency)
    SELECT DISTINCT 
        TRIM(split_part(line, ',', 2)), 
        'TGO' AS price_source_code,     
        'Tiingo Market (' || TRIM(split_part(line, ',', 2)) || ')' AS name,
        'Unknown' AS country,
        CASE WHEN LENGTH(TRIM(split_part(line, ',', 4))) = 3 THEN TRIM(split_part(line, ',', 4)) ELSE NULL END AS currency
    FROM temp_tiingo
    WHERE TRIM(split_part(line, ',', 2)) != ''
    ON CONFLICT (code, price_source_code) DO NOTHING;

    -- =========================================================================
    -- SCHRITT 2: Ticker importieren (Jetzt mit GROUP BY gegen interne CSV-Duplikate!)
    -- =========================================================================
    INSERT INTO shared.exchange_tickers (
        ticker_code, 
        exchange_code, 
        price_source_code, 
        name, 
        country, 
        currency, 
        type, 
        is_active, 
        updated_at
    )
    SELECT 
        TRIM(split_part(line, ',', 1)) AS ticker_code, 
        TRIM(split_part(line, ',', 2)) AS exchange_code, 
        'TGO' AS price_source_code,     
        MAX(TRIM(split_part(line, ',', 1)) || ' (' || TRIM(split_part(line, ',', 3)) || ')') AS name,
        'Unknown' AS country,
        MAX(CASE WHEN LENGTH(TRIM(split_part(line, ',', 4))) = 3 THEN TRIM(split_part(line, ',', 4)) ELSE NULL END) AS currency,
        MAX(TRIM(split_part(line, ',', 3))) AS type,
        TRUE AS is_active,
        NOW() AS updated_at
    FROM temp_tiingo
    WHERE TRIM(split_part(line, ',', 1)) != '' AND TRIM(split_part(line, ',', 2)) != ''
    -- Das GROUP BY eliminiert alle identischen Zeilen-Kombinationen aus der Datei, BEVOR das Insert triggert!
    GROUP BY TRIM(split_part(line, ',', 1)), TRIM(split_part(line, ',', 2))
    ON CONFLICT (ticker_code, exchange_code, price_source_code) 
    DO UPDATE SET 
        type = EXCLUDED.type,
        currency = EXCLUDED.currency,
        updated_at = NOW();

    RAISE NOTICE 'Tiingo CSV-Import erfolgreich und duplikatbereinigt abgeschlossen!';
END $$;







-- RESTORE BACKUP DATA

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'backup' 
          AND table_name = 'asset_static_data'
    ) THEN
        EXECUTE '
            INSERT INTO shared.asset_static_data (
                isin,
                name,
                risk_currency,
                instrument_type_code,
                asset_class_code,
                region_code,
                sector_code,
                industry,
                country,
                closed_on,
                price_source_code,
                price_currency,
                price_start_date,
                ticker,
                created_at,
                created_by,
                updated_at,
                updated_by
            )
            SELECT 
                isin,
                name,
                risk_currency,
                instrument_type_code,
                asset_class_code,
                region_code,
                sector_code,
                industry,
                country,
                closed_on,
                price_source_code,
                price_currency,
                price_start_date,
                ticker,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM backup.asset_static_data
        ';
    END IF;
END $$;
