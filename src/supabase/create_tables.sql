-- 1. Create Reference Tables if they don't exist
CREATE TABLE IF NOT EXISTS ref_asset_class (
  code TEXT PRIMARY KEY,
  label TEXT NOT NULL
);

INSERT INTO ref_asset_class (code, label)
VALUES 
  ('LIQ', 'Liquidity'),
  ('BON', 'Bonds & Bond Funds'),
  ('EQU', 'Equities & Equity Funds'),
  ('ALT', 'Alternative Investments')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;



CREATE TABLE IF NOT EXISTS ref_region (
  code TEXT PRIMARY KEY,
  label TEXT NOT NULL
);

INSERT INTO ref_region (code, label)
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


CREATE TABLE IF NOT EXISTS ref_sector (
  code TEXT PRIMARY KEY,
  label TEXT NOT NULL
);

INSERT INTO ref_sector (code, label)
VALUES 
  ('10', 'Energy'), ('15', 'Materials'), ('20', 'Industrials'),
  ('25', 'Consumer Discretionary'), ('30', 'Consumer Staples'),
  ('35', 'Health Care'), ('40', 'Financials'), ('45', 'Information Technology'),
  ('50', 'Communication Services'), ('55', 'Utilities'), ('60', 'Real Estate')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


CREATE TABLE IF NOT EXISTS ref_price_source (
  code TEXT PRIMARY KEY,
  label TEXT NOT NULL
);

INSERT INTO ref_price_source (code, label)
VALUES 
  ('GFN', 'GOOGLEFINANCE'),
  ('ARV', 'ARIVA')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;



-- 2. Create the Main Table if it doesn't exist
CREATE TABLE IF NOT EXISTS asset_static_data (
  isin VARCHAR(12) PRIMARY KEY,
  name TEXT NOT NULL,
  currency VARCHAR(3),
  ticker TEXT,

  -- Foreign Key References  
  price_source TEXT REFERENCES ref_price_source(code),
  asset_class_code TEXT REFERENCES ref_asset_class(code),
  region_code TEXT REFERENCES ref_region(code),
  sector_code TEXT REFERENCES ref_sector(code),

  closed_on DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by TEXT
);





-- 1. Create reference table for transaction types
CREATE TABLE IF NOT EXISTS ref_type (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

-- 2. Insert or update data for RefType
INSERT INTO ref_type (code, label)
VALUES ('B', 'Buy'), ('S', 'Sell')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;

-- 3. Create Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    username TEXT NOT NULL,
    account_code TEXT NOT NULL,
    description TEXT,
    PRIMARY KEY (username, account_code)
);

-- 4. Insert or update data for Accounts
INSERT INTO accounts (username, account_code, description)
VALUES 
    ('mirko', 'SMB', 'Smartbroker'),
    ('mirko', 'ING', 'ING-DiBa'),
    ('mirko', 'CON', 'Consorsbank'),
    ('anja' , 'SMB', 'Smartbroker'),
    ('anja' , 'DKB', 'DKB')
ON CONFLICT (username, account_code) DO UPDATE SET description = EXCLUDED.description;

-- 5. Create Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    username TEXT NOT NULL,
    id TEXT NOT NULL,
    account_code TEXT NOT NULL,
    isin TEXT,
    date DATE DEFAULT CURRENT_DATE,
    type_code TEXT,
    quantity NUMERIC,
    total_amount_eur NUMERIC,
    
    PRIMARY KEY (username, id),
    
    CONSTRAINT fk_ref_type
        FOREIGN KEY (type_code) REFERENCES ref_type(code)
        ON DELETE SET NULL,
        
    CONSTRAINT fk_accounts
        FOREIGN KEY (username, account_code) REFERENCES accounts(username, account_code)
        ON DELETE CASCADE
);

