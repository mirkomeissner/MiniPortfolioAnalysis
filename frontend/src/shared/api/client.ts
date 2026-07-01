import type {
  AccountRecord,
  AssetCreateRequest,
  AssetRecord,
  AuthLoginRequest,
  AuthLoginResponse,
  HoldingRecord,
  HoldingsDateRangeResponse,
  MissingIsinsResponse,
  ReferenceBootstrapResponse,
  TransactionCreateRequest,
  TransactionDeleteAllResponse,
  TransactionImportMappingConfig,
  TransactionImportBulkRequest,
  TransactionImportBulkResponse,
  TransactionImportPreviewRequest,
  TransactionImportPreviewResponse,
  TransactionImportSettingsResponse,
  TransactionImportSettingsSaveResponse,
  TransactionRecord,
} from '../types/api'

const configuredBaseUrl = import.meta.env.VITE_BACKEND_API_URL?.trim().replace(/\/$/, '')
const apiBaseUrl = configuredBaseUrl ?? ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  token?: string
  userId?: string
  body?: unknown
}

function withQuery(path: string, query: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) {
      searchParams.set(key, String(value))
    }
  }

  const queryString = searchParams.toString()
  if (!queryString) {
    return path
  }
  return `${path}?${queryString}`
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`
  }

  if (options.userId) {
    headers['X-User-Id'] = options.userId
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  const text = await response.text()
  const payload = text ? (JSON.parse(text) as unknown) : null

  if (!response.ok) {
    const detail =
      payload !== null && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail?: unknown }).detail)
        : response.statusText
    throw new ApiError(detail || 'Request failed', response.status)
  }

  return payload as T
}

export async function login(payload: AuthLoginRequest): Promise<AuthLoginResponse> {
  return requestJson<AuthLoginResponse>('/auth/login', {
    method: 'POST',
    body: payload,
  })
}

export async function listAccounts(userId: string, token?: string): Promise<AccountRecord[]> {
  return requestJson<AccountRecord[]>(withQuery('/accounts', { user_id: userId }), {
    token,
    userId,
  })
}

export async function createAccount(
  userId: string,
  accountCode: string,
  description: string,
  token?: string,
): Promise<AccountRecord> {
  return requestJson<AccountRecord>('/accounts', {
    method: 'POST',
    token,
    userId,
    body: {
      user_id: userId,
      account_code: accountCode,
      description,
    },
  })
}

export async function updateAccount(
  userId: string,
  accountCode: string,
  description: string,
  token?: string,
): Promise<AccountRecord> {
  return requestJson<AccountRecord>(`/accounts/${encodeURIComponent(accountCode)}`, {
    method: 'PUT',
    token,
    userId,
    body: {
      user_id: userId,
      description,
    },
  })
}

export async function listAssets(token?: string, userId?: string): Promise<AssetRecord[]> {
  return requestJson<AssetRecord[]>('/assets', {
    token,
    userId,
  })
}

export async function createAsset(payload: AssetCreateRequest, userId: string, token?: string): Promise<AssetCreateRequest> {
  return requestJson<AssetCreateRequest>('/assets', {
    method: 'POST',
    token,
    userId,
    body: payload,
  })
}

export async function listHoldings(userId: string, holdingDate: string, token?: string): Promise<HoldingRecord[]> {
  return requestJson<HoldingRecord[]>(
    withQuery('/holdings', {
      user_id: userId,
      holding_date: holdingDate,
    }),
    {
      token,
      userId,
    },
  )
}

export async function getHoldingsDateRange(userId: string, token?: string): Promise<HoldingsDateRangeResponse> {
  return requestJson<HoldingsDateRangeResponse>(withQuery('/holdings/date-range', { user_id: userId }), {
    token,
    userId,
  })
}

export async function getReferenceBootstrap(userId: string, token?: string): Promise<ReferenceBootstrapResponse> {
  return requestJson<ReferenceBootstrapResponse>(withQuery('/references/bootstrap', { user_id: userId }), {
    token,
    userId,
  })
}

export async function listTransactions(userId: string, token?: string): Promise<TransactionRecord[]> {
  return requestJson<TransactionRecord[]>(withQuery('/transactions', { user_id: userId }), {
    token,
    userId,
  })
}

export async function createTransaction(payload: TransactionCreateRequest, token?: string): Promise<TransactionCreateRequest> {
  return requestJson<TransactionCreateRequest>('/transactions', {
    method: 'POST',
    token,
    userId: payload.user_id,
    body: payload,
  })
}

export async function deleteAllTransactions(userId: string, token?: string): Promise<TransactionDeleteAllResponse> {
  return requestJson<TransactionDeleteAllResponse>(withQuery('/transactions', { user_id: userId }), {
    method: 'DELETE',
    token,
    userId,
  })
}

export async function getTransactionImportSettings(
  userId: string,
  accountCode: string,
  token?: string,
): Promise<TransactionImportSettingsResponse> {
  return requestJson<TransactionImportSettingsResponse>(
    withQuery('/transactions/import-settings', {
      user_id: userId,
      account_code: accountCode,
    }),
    {
      token,
      userId,
    },
  )
}

export async function saveTransactionImportSettings(
  userId: string,
  accountCode: string,
  mappingConfig: TransactionImportMappingConfig,
  token?: string,
): Promise<TransactionImportSettingsSaveResponse> {
  return requestJson<TransactionImportSettingsSaveResponse>('/transactions/import-settings', {
    method: 'PUT',
    token,
    userId,
    body: {
      user_id: userId,
      account_code: accountCode,
      mapping_config: mappingConfig,
    },
  })
}

export async function getMissingIsins(isins: string[], userId: string, token?: string): Promise<string[]> {
  const response = await requestJson<MissingIsinsResponse>('/transactions/missing-isins', {
    method: 'POST',
    token,
    userId,
    body: {
      isins,
    },
  })

  return response.missing_isins
}

export async function getTransactionImportPreview(
  payload: TransactionImportPreviewRequest,
  token?: string,
): Promise<TransactionImportPreviewResponse> {
  return requestJson<TransactionImportPreviewResponse>('/transactions/import-preview', {
    method: 'POST',
    token,
    userId: payload.user_id,
    body: payload,
  })
}

export async function importTransactionsBulk(
  payload: TransactionImportBulkRequest,
  token?: string,
): Promise<TransactionImportBulkResponse> {
  return requestJson<TransactionImportBulkResponse>('/transactions/import-bulk', {
    method: 'POST',
    token,
    userId: payload.user_id,
    body: payload,
  })
}
