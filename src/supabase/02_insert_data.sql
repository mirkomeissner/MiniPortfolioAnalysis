INSERT INTO ref_asset_class (code, label)
VALUES 
  ('LIQ', 'Liquidity'),
  ('BON', 'Bonds & Bond Funds'),
  ('EQU', 'Equities & Equity Funds'),
  ('ALT', 'Alternative Investments')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


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


INSERT INTO ref_sector (code, label)
VALUES 
  ('10', 'Energy'), ('15', 'Materials'), ('20', 'Industrials'),
  ('25', 'Consumer Discretionary'), ('30', 'Consumer Staples'),
  ('35', 'Health Care'), ('40', 'Financials'), ('45', 'Information Technology'),
  ('50', 'Communication Services'), ('55', 'Utilities'), ('60', 'Real Estate')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;


INSERT INTO ref_price_source (code, label)
VALUES 
  ('GFN', 'GOOGLEFINANCE'),
  ('ARV', 'ARIVA')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;





INSERT INTO ref_type (code, label)
VALUES ('B', 'Buy'), ('S', 'Sell')
ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label;



INSERT INTO accounts (username, account_code, description)
VALUES 
    ('mirko', 'SMB', 'Smartbroker'),
    ('mirko', 'ING', 'ING-DiBa'),
    ('mirko', 'CON', 'Consorsbank'),
    ('anja' , 'SMB', 'Smartbroker'),
    ('anja' , 'DKB', 'DKB')
ON CONFLICT (username, account_code) DO UPDATE SET description = EXCLUDED.description;

