

INSERT INTO shared.ref_asset_class (code, label, color_hex, display_order)
VALUES 
    ('LIQ', 'Liquidity',               '#2CA58D', 10),
    ('BON', 'Bonds & Bond Funds',      '#4C78A8', 20),
    ('EQU', 'Equities & Equity Funds', '#F58518', 30),
    ('ALT', 'Alternative Investments', '#B279A2', 40)
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, color_hex = EXCLUDED.color_hex, display_order = EXCLUDED.display_order;


INSERT INTO shared.ref_region (code, label, color_hex, display_order)
VALUES 
    ('GLO',  'Global / World',         '#577590', 10),
    ('DEV',  'Developed Markets',      '#277DA1', 20),
    ('USA',  'United States',          '#1D3557', 30),
    ('NAM',  'North America (Ex-USA)', '#4D96FF', 40),
    ('EUR',  'Europe',                 '#4361EE', 50),
    ('UK',   'United Kingdom',         '#7209B7', 60),
    ('APAC', 'Asia Pacific',           '#43AA8B', 70),
    ('EM',   'Emerging Markets',       '#F8961E', 80),
    ('MEAF', 'Middle East & Africa',   '#C77D1F', 90),
    ('LATM', 'Latin America',          '#F94144', 100)
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, color_hex = EXCLUDED.color_hex, display_order = EXCLUDED.display_order;


INSERT INTO shared.ref_sector (code, label, color_hex, display_order)
VALUES 
    ('10', 'Energy',                 '#F94144', 10), 
    ('15', 'Materials',              '#F3722C', 15), 
    ('20', 'Industrials',            '#F8961E', 20),
    ('25', 'Consumer Discretionary', '#F9C74F', 25), 
    ('30', 'Consumer Staples',       '#90BE6D', 30),
    ('35', 'Health Care',            '#43AA8B', 35), 
    ('40', 'Financials',             '#577590', 40), 
    ('45', 'Information Technology', '#277DA1', 45),
    ('50', 'Communication Services', '#9D4EDD', 50), 
    ('55', 'Utilities',              '#4D908E', 55), 
    ('60', 'Real Estate',            '#B56576', 60)
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, color_hex = EXCLUDED.color_hex, display_order = EXCLUDED.display_order;


INSERT INTO shared.ref_price_source (code, label)
VALUES 
  ('YFN', 'YFINANCE'),
  ('ISH', 'iShares'),
  ('TGO', 'TIINGO'),
  ('MKS', 'MARKETSTACK'),
  ('EODHD', 'EOD HISTORICAL DATA')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO shared.ref_instrument_type (code, label, color_hex, display_order)
VALUES 
    ('STO', 'Stock',       '#277DA1', 10),
    ('BON', 'Bond',        '#577590', 20),
    ('FUN', 'Fund',        '#90BE6D', 30),
    ('ETF', 'ETF',         '#43AA8B', 40),
    ('CER', 'Certificate', '#F94144', 50)
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, color_hex = EXCLUDED.color_hex, display_order = EXCLUDED.display_order;


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
        'eodhd_WAR.json', 
        'eodhd_AU.json'
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



/*


DO $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Richtige User-ID anhand der E-Mail ermitteln
    SELECT id INTO v_user_id FROM public.users WHERE email = 'to_be_specified@mail.com';

    -- Falls der User nicht existiert, wird ein Fehler geworfen
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User mit der E-Mail to_be_specified@mail.com wurde nicht gefunden!';
    END IF;

    -- Inserte die Asset-Daten
    INSERT INTO shared.asset_static_data 
        (isin, name, risk_currency, instrument_type_code, asset_class_code, region_code, sector_code, industry, country, closed_on, price_source_code, price_currency, price_start_date, ticker, created_at, created_by, updated_at, updated_by)
    VALUES
        ('GB00BMHVL512', 'Klarna Group plc', 'USD', 'STO', 'EQU', 'USA', '40', 'Credit Services', 'Sweden', NULL, 'TGO', 'USD', '2026-03-16', 'KLAR', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 16:52:39.272548+00', v_user_id),
        ('US87918A1051', 'Teladoc Health Inc.', 'USD', 'STO', 'EQU', 'USA', '35', 'Health Information Services', 'United States', NULL, 'TGO', 'USD', '2025-10-23', 'TDOC', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:14:44.996568+00', v_user_id),
        ('DE000A1ML7J1', 'Vonovia SE', 'EUR', 'STO', 'EQU', 'EUR', '60', 'Real Estate Services', 'Germany', NULL, 'EODHD', 'EUR', '2025-12-17', 'VNA.XETRA', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 17:02:32.879999+00', v_user_id),
        ('NL0013056914', 'Elastic N.V.', 'USD', 'STO', 'EQU', 'EUR', '45', 'Software - Application', 'Netherlands', NULL, 'TGO', 'USD', '2025-10-08', 'ESTC', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:31:24.510499+00', v_user_id),
        ('DE000A3E00M1', 'IONOS Group SE', 'EUR', 'STO', 'EQU', 'EUR', '45', 'Information Technology Services', 'Germany', NULL, 'EODHD', 'EUR', '2026-03-23', 'IOS.XETRA', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 17:01:09.36247+00', v_user_id),
        ('US90364P1057', 'UiPath Inc.', 'USD', 'STO', 'EQU', 'USA', '45', 'Software - Infrastructure', 'United States', NULL, 'TGO', 'USD', '2026-01-15', 'PATH', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:12:27.919223+00', v_user_id),
        ('US91688F1049', 'Upwork Inc.', 'USD', 'STO', 'EQU', 'USA', '50', 'Internet Content & Information', 'United States', NULL, 'TGO', 'USD', '2025-11-14', 'UPWK', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-26 22:18:27.077577+00', v_user_id),
        ('US8636671013', 'Stryker Corporation', 'USD', 'STO', 'EQU', 'USA', '35', 'Medical Devices', 'United States', NULL, 'TGO', 'USD', '2025-12-22', 'SYK', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:15:21.868198+00', v_user_id),
        ('US7427181091', 'Procter & Gamble Company', 'USD', 'STO', 'EQU', 'USA', '30', 'Household & Personal Products', 'United States', NULL, 'TGO', 'USD', '2025-10-07', 'PG', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:16:23.815498+00', v_user_id),
        ('US7134481081', 'PepsiCo Inc.', 'USD', 'STO', 'EQU', 'USA', '30', 'Beverages - Non-Alcoholic', 'United States', NULL, 'TGO', 'USD', '2026-03-31', 'PEP', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:17:00.877214+00', v_user_id),
        ('US70450Y1038', 'PayPal Holdings Inc.', 'USD', 'STO', 'EQU', 'USA', '40', 'Credit Services', 'United States', NULL, 'TGO', 'USD', '2025-10-29', 'PYPL', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:18:18.298025+00', v_user_id),
        ('US68389X1054', 'Oracle Corporation', 'USD', 'STO', 'EQU', 'USA', '45', 'Software - Infrastructure', 'United States', NULL, 'TGO', 'USD', '2025-12-19', 'ORCL', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:19:06.262114+00', v_user_id),
        ('US58733R1023', 'MercadoLibre Inc.', 'USD', 'STO', 'EQU', 'LATM', '25', 'Internet Retail', 'Uruguay', NULL, 'TGO', 'USD', '2025-12-19', 'MELI', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:19:45.839348+00', v_user_id),
        ('US55087P1049', 'Lyft Inc.', 'USD', 'STO', 'EQU', 'USA', '45', 'Software - Application', 'United States', NULL, 'TGO', 'USD', '2025-12-17', 'LYFT', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:20:23.314575+00', v_user_id),
        ('US4592001014', 'International Business Machines', 'USD', 'STO', 'EQU', 'USA', '45', 'Information Technology Services', 'United States', NULL, 'TGO', 'USD', '2025-12-17', 'IBM', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:21:23.615251+00', v_user_id),
        ('US19260Q1076', 'Coinbase Global Inc.', 'USD', 'STO', 'EQU', 'USA', '40', 'Financial Data & Stock Exchanges', 'United States', NULL, 'TGO', 'USD', '2025-12-17', 'COIN', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:22:34.904434+00', v_user_id),
        ('US1667641005', 'Chevron Corporation', 'USD', 'STO', 'EQU', 'USA', '10', 'Oil & Gas Integrated', 'United States', NULL, 'TGO', 'USD', '2026-01-05', 'CVX', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:23:06.030894+00', v_user_id),
        ('US12503M1080', 'Cboe Global Markets Inc.', 'USD', 'STO', 'EQU', 'USA', '40', 'Financial Data & Stock Exchanges', 'United States', NULL, 'TGO', 'USD', '2025-11-26', 'CBOE', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:24:11.336283+00', v_user_id),
        ('US0231351067', 'Amazon.com Inc.', 'USD', 'STO', 'EQU', 'USA', '25', 'Internet Retail', 'United States', NULL, 'TGO', 'USD', '2026-01-15', 'AMZN', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:24:46.78927+00', v_user_id),
        ('US02079K3059', 'Alphabet Inc. Class A', 'USD', 'STO', 'EQU', 'USA', '50', 'Internet Content & Information', 'United States', NULL, 'TGO', 'USD', '2026-01-15', 'GOOGL', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:25:25.248229+00', v_user_id),
        ('US0090661010', 'Airbnb Inc.', 'USD', 'STO', 'EQU', 'USA', '25', 'Travel Services', 'United States', NULL, 'TGO', 'USD', '2025-12-17', 'ABNB', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:25:59.613542+00', v_user_id),
        ('US00183L2016', 'ANGI Homeservices Inc.', 'USD', 'STO', 'EQU', 'USA', '50', 'Internet Content & Information', 'United States', NULL, 'TGO', 'USD', '2025-10-10', 'ANGI', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:26:53.663335+00', v_user_id),
        ('SE0007692850', 'Camurus AB', 'SEK', 'STO', 'EQU', 'EUR', '35', 'Biotechnology', 'Sweden', NULL, 'EODHD', 'SEK', '2026-04-01', 'CAMX.ST', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:27:37.566243+00', v_user_id),
        ('IE00BHZRQZ17', 'Franklin FTSE India UCITS ETF (Acc)', 'USD', 'ETF', 'EQU', 'EM', NULL, NULL, 'India', NULL, 'EODHD', 'USD', '2025-12-12', 'FLXI.LSE', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-23 17:52:17.36313+00', v_user_id),
        ('IL0011762130', 'Monday.Com Ltd.', 'USD', 'STO', 'EQU', 'MEAF', '45', 'Software - Application', 'Israel', NULL, 'TGO', 'USD', '2025-12-02', 'MNDY', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:44:35.981155+00', v_user_id),
        ('IL0010830961', 'SuperCom Ltd.', 'USD', 'STO', 'EQU', 'MEAF', '20', 'Security & Protection Services', 'Israel', NULL, 'TGO', 'USD', '2026-03-02', 'SPCB', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:45:08.794889+00', v_user_id),
        ('IE0032895942', 'iShares USD Corp Bond UCITS ETF (Dist)', 'USD', 'ETF', 'BON', 'GLO', NULL, '', '', NULL, 'ISH', 'USD', '2025-12-12', '251832', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:05:09.362636+00', v_user_id),
        ('IE00BG0J4B71', 'iShares Broad EUR High Yield Corp Bond UCITS ETF (Dist)', 'EUR', 'ETF', 'BON', 'GLO', NULL, NULL, NULL, NULL, 'ISH', 'EUR', '2026-02-05', '326124', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:48:34.084826+00', v_user_id),
        ('NL0011683594', 'VanEck Morningstar Developed Markets Dividend Leaders UCITS ETF (Dist)', 'EUR', 'ETF', 'EQU', 'DEV', NULL, NULL, NULL, NULL, 'EODHD', 'EUR', '2025-12-22', 'TDIV.AS', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-23 17:51:35.909776+00', v_user_id),
        ('IE000U9ODG19', 'iShares Global Aerospace & Defence UCITS ETF USD (Acc)', 'USD', 'ETF', 'EQU', 'GLO', NULL, NULL, NULL, NULL, 'ISH', 'USD', '2026-01-20', '334464', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 21:11:10.307052+00', v_user_id),
        ('IE000VVBM1F6', 'iShares iBonds Dec 2034 Term USD Corp UCITS ETF (Dist)', 'USD', 'ETF', 'BON', 'USA', NULL, '', 'United States', NULL, 'ISH', 'USD', '2026-02-05', '339390', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:44:49.300416+00', v_user_id),
        ('IE00B0M63177', 'iShares MSCI EM UCITS ETF USD (Dist)', 'USD', 'ETF', 'EQU', 'EM', NULL, NULL, NULL, NULL, 'ISH', 'USD', '2026-02-05', '251857', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:36:56.971986+00', v_user_id),
        ('LU2082997946', 'Amundi STOXX Europe 600 Insurance UCITS ETF (Dist)', 'EUR', 'ETF', 'EQU', 'EUR', NULL, NULL, NULL, NULL, 'EODHD', 'EUR', '2026-02-05', 'EGV1.XETRA', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-23 17:51:14.819035+00', v_user_id),
        ('IE00B1TXHL60', 'iShares Listed Private Equity UCITS ETF USD (Dist)', 'USD', 'ETF', 'EQU', 'GLO', NULL, NULL, NULL, NULL, 'ISH', 'USD', '2025-12-17', '251918', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:41:05.131959+00', v_user_id),
        ('IE00B74DQ490', 'iShares Global High Yield Corp Bond UCITS ETF USD (Dist)', 'USD', 'ETF', 'BON', 'GLO', NULL, '', '', NULL, 'ISH', 'USD', '2026-02-05', '251814', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:45:48.839315+00', v_user_id),
        ('IE00BYZTVT56', 'iShares EUR Corp Bond ESG SRI UCITS ETF (Dist)', 'EUR', 'ETF', 'BON', 'GLO', NULL, NULL, NULL, NULL, 'ISH', 'EUR', '2026-02-05', '297933', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:47:42.073176+00', v_user_id),
        ('ES0118594417', 'Indra Sistemas S.A.', 'EUR', 'STO', 'EQU', 'EUR', '45', 'Information Technology Services', 'Spain', NULL, 'EODHD', 'EUR', '2025-12-17', 'IDR.MC', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 16:58:25.932631+00', v_user_id),
        ('DK0062498333', 'Novo Nordisk A/S', 'DKK', 'STO', 'EQU', 'EUR', '35', 'Drug Manufacturers - General', 'Denmark', NULL, 'EODHD', 'DKK', '2025-12-16', 'NOVO-B.CO', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 16:59:02.079217+00', v_user_id),
        ('DE0007030009', 'Rheinmetall AG', 'EUR', 'STO', 'EQU', 'EUR', '20', 'Aerospace & Defense', 'Germany', NULL, 'EODHD', 'EUR', '2026-01-12', 'RHM.XETRA', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 17:03:21.215391+00', v_user_id),
        ('IE00BK4W7N32', 'iShares USD Corporate Bond ESG SRI UCITS ETF (Dist)', 'USD', 'ETF', 'BON', 'GLO', NULL, NULL, NULL, NULL, 'ISH', 'USD', '2025-12-09', '310473', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-18 20:03:59.051373+00', v_user_id),
        ('GB00B10RZP78', 'Unilever OLD before SpinOff', 'GBP', 'STO', 'EQU', 'UK', '30', 'Household & Personal Products', 'United Kingdom', '2026-06-23', 'EODHD', 'GBX', '2025-10-07', 'ULVR.LSE', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-06-23 18:04:15.500651+00', v_user_id),
        ('DE0007164600', 'SAP SE', 'EUR', 'STO', 'EQU', 'EUR', '45', 'Software - Application', 'Germany', NULL, 'EODHD', 'EUR', '2024-12-31', 'SAP.XETRA', '2026-04-22 19:28:02.103062+00', v_user_id, '2026-05-28 20:21:18.19322+00', v_user_id),
        ('US90353T1007', 'Uber Technologies Inc.', 'USD', 'STO', 'EQU', 'USA', '45', 'Software - Application', 'United States', NULL, 'TGO', 'USD', '2025-12-17', 'UBER', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:13:11.140045+00', v_user_id),
        ('US37637K1088', 'GitLab Inc.', 'USD', 'STO', 'EQU', 'USA', '45', 'Software - Infrastructure', 'United States', NULL, 'TGO', 'USD', '2025-12-02', 'GTLB', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:21:56.902744+00', v_user_id),
        ('PLGPW0000017', 'Gielda PapierĂłw Wartosciowych w Warszawie S.A.', 'PLN', 'STO', 'EQU', 'EM', '40', 'Financial Data & Stock Exchanges', 'Poland', NULL, 'EODHD', 'PLN', '2025-12-09', 'GPW.WAR', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:29:09.462429+00', v_user_id),
        ('NL0015002MS2', 'The Magnum Ice Cream Company N.V.', 'EUR', 'STO', 'EQU', 'EUR', '30', 'Packaged Foods', 'Netherlands', NULL, 'EODHD', 'EUR', '2025-12-08', 'MICC.AS', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 13:30:24.630188+00', v_user_id),
        ('GB00BVZK7T90', 'Unilever PLC', 'GBP', 'STO', 'EQU', 'UK', '30', 'Household & Personal Products', 'United Kingdom', NULL, 'EODHD', 'GBX', '2025-12-09', 'ULVR.LSE', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 16:43:32.912237+00', v_user_id),
        ('GB00B1XH2C03', 'Ferrexpo plc', 'USD', 'STO', 'EQU', 'EUR', '15', 'Steel', 'Switzerland', NULL, 'EODHD', 'GBX', '2025-11-18', 'FXPO.LSE', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 16:55:43.432075+00', v_user_id),
        ('DE000HAG0005', 'Hensoldt AG', 'EUR', 'STO', 'EQU', 'EUR', '20', 'Aerospace & Defense', 'Germany', NULL, 'EODHD', 'EUR', '2025-12-08', 'HAG.XETRA', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 17:00:12.151309+00', v_user_id),
        ('AU000000DRO2', 'DroneShield Limited', 'AUD', 'STO', 'EQU', 'APAC', '20', 'Aerospace & Defense', 'Australia', NULL, 'EODHD', 'AUD', '2025-10-16', 'DRO.AU', '2026-04-18 18:04:36.842283+00', v_user_id, '2026-05-30 17:10:05.973903+00', v_user_id);
END $$;


*/