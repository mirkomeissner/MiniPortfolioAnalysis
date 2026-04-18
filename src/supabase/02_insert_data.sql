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
  ('ARV', 'ARIVA')
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

  -- Middle East & Africa
  ('ILS', 'Israeli New Shekel'),
  ('TRY', 'Turkish Lira'),
  ('AED', 'UAE Dirham'),
  ('SAR', 'Saudi Riyal'),
  ('QAR', 'Qatari Rial'),
  ('ZAR', 'South African Rand'),
  ('EGP', 'Egyptian Pound'),

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









-- Insert users into public.users
-- The ID (UUID) is generated automatically
INSERT INTO public.users (username, email)
VALUES 
    ('mirko', NULL),
    ('anja', NULL);

-- Insert accounts using the UUIDs from the users table
INSERT INTO public.accounts (user_id, account_code, description)
VALUES 
    ((SELECT id FROM public.users WHERE username = 'mirko'), 'SMB', 'Smartbroker'),
    ((SELECT id FROM public.users WHERE username = 'mirko'), 'ING', 'ING-DiBa'),
    ((SELECT id FROM public.users WHERE username = 'mirko'), 'CON', 'Consorsbank'),
    ((SELECT id FROM public.users WHERE username = 'anja'),  'SMB', 'Smartbroker'),
    ((SELECT id FROM public.users WHERE username = 'anja'),  'DKB', 'DKB')
ON CONFLICT (user_id, account_code) 
DO UPDATE SET description = EXCLUDED.description;
