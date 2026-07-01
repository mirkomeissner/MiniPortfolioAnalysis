export type AuthLoginRequest = {
  email: string
  password: string
}

export type AuthLoginResponse = {
  authenticated: boolean
  access_token: string | null
  user_id: string | null
  username: string | null
  email: string | null
  is_approved: boolean
  pending_email: string | null
}

export type AccountRecord = {
  account_code: string
  description: string | null
}

export type HoldingRecord = {
  user_id: string | null
  account_code: string | null
  holding_date: string | null
  isin: string | null
  quantity: number | null
  price_currency: string | null
  price: number | null
  valuation_in_price_currency: number | null
  fx_to_eur: number | null
  valuation_in_eur: number | null
  asset_name: string | null
  asset_ticker: string | null
  asset_risk_currency: string | null
  asset_type: string | null
  asset_class: string | null
  asset_region: string | null
  asset_sector: string | null
  asset_industry: string | null
  asset_country: string | null
}

export type HoldingsDateRangeResponse = {
  user_id: string
  first_date: string | null
  last_date: string
}

export type AssetRecord = {
  isin: string | null
  name: string | null
  ticker: string | null
  risk_currency: string | null
  instrument_type: string | null
  asset_class: string | null
  region: string | null
  sector: string | null
  industry: string | null
  country: string | null
  price_source: string | null
  price_currency: string | null
  price_start_date: string | null
  closed_on: string | null
  created_at: string | null
  created_by: string | null
  updated_at: string | null
  updated_by: string | null
}

export type AssetCreateRequest = {
  isin: string
  name?: string | null
  price_start_date?: string | null
  created_by?: string | null
}

export type TransactionRecord = {
  trade_date: string | null
  account: string | null
  isin: string | null
  name: string | null
  transaction_type: string | null
  quantity: number | null
  settle_amount: number | null
  settle_currency: string | null
  fx_rate: number | null
  amount_eur: number | null
  created_at: string | null
  updated_at: string | null
  internal_id: string | null
}

export type TransactionCreateRequest = {
  user_id: string
  id?: string
  account_code: string
  isin: string
  date: string
  transaction_type_code: string
  quantity: number | null
  settle_amount: number | null
  settle_currency: string | null
  settle_fxrate: number | null
  amount_eur: number | null
}

export type TransactionImportMappingConfig = {
  map_isin?: string
  map_date?: string
  map_type?: string
  map_quantity?: string
  map_settle_amount?: string
  map_settle_currency?: string
  map_settle_fxrate?: string
  map_amount_eur?: string
}

export type TransactionImportSettingsResponse = {
  mapping_config: TransactionImportMappingConfig | null
}

export type TransactionImportSettingsSaveResponse = {
  user_id: string
  account_code: string
  saved: boolean
}

export type MissingIsinsResponse = {
  missing_isins: string[]
}

export type TransactionDeleteAllResponse = {
  user_id: string
  deleted: boolean
}

export type TransactionImportPreviewRequest = {
  user_id: string
  account_code: string
  csv_content: string
  mapping_config: TransactionImportMappingConfig
}

export type TransactionImportPreviewRow = {
  user_id: string
  account_code: string
  isin: string
  date: string
  transaction_type_code: string
  quantity: number
  settle_amount: number
  settle_currency: string
  settle_fxrate: number
  amount_eur: number
}

export type TransactionImportPreviewResponse = {
  rows: TransactionImportPreviewRow[]
  missing_isins: string[]
  existing_ids: string[]
  duplicate_overlap_count: number
}

export type TransactionImportBulkRequest = {
  user_id: string
  rows: TransactionImportPreviewRow[]
  duplicate_strategy: 'allow' | 'skip'
}

export type TransactionImportBulkResponse = {
  saved_count: number
  skipped_overlap_count: number
}

export type ReferenceBootstrapResponse = {
  opt_asset: string[]
  opt_gics: string[]
  opt_region: string[]
  opt_type: string[]
  opt_source: string[]
  opt_trans_types: string[]
  opt_accounts: string[]
  opt_assets: string[]
  db_region_map: Record<string, string>
  type_logic_map: Record<string, { quantity_sign: number | null; amount_sign: number | null }>
}

export type SessionState = {
  accessToken: string
  userId: string
  username: string
  email: string
}
