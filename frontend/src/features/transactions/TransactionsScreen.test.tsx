import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TransactionsScreen } from './TransactionsScreen'

const {
  listTransactionsMock,
  getReferenceBootstrapMock,
  getTransactionImportPreviewMock,
  createAssetMock,
  createTransactionMock,
  importTransactionsBulkMock,
  deleteAllTransactionsMock,
  getTransactionImportSettingsMock,
  saveTransactionImportSettingsMock,
} = vi.hoisted(() => ({
  listTransactionsMock: vi.fn(),
  getReferenceBootstrapMock: vi.fn(),
  getTransactionImportPreviewMock: vi.fn(),
  createAssetMock: vi.fn(),
  createTransactionMock: vi.fn(),
  importTransactionsBulkMock: vi.fn(),
  deleteAllTransactionsMock: vi.fn(),
  getTransactionImportSettingsMock: vi.fn(),
  saveTransactionImportSettingsMock: vi.fn(),
}))

vi.mock('../../shared/api/client', () => ({
  listTransactions: listTransactionsMock,
  getReferenceBootstrap: getReferenceBootstrapMock,
  getTransactionImportPreview: getTransactionImportPreviewMock,
  createAsset: createAssetMock,
  createTransaction: createTransactionMock,
  importTransactionsBulk: importTransactionsBulkMock,
  deleteAllTransactions: deleteAllTransactionsMock,
  getTransactionImportSettings: getTransactionImportSettingsMock,
  saveTransactionImportSettings: saveTransactionImportSettingsMock,
}))

describe('TransactionsScreen', () => {
  const session = {
    accessToken: 'token',
    userId: 'user-1',
    username: 'test-user',
    email: 'test@example.com',
  }

  beforeEach(() => {
    vi.clearAllMocks()

    getReferenceBootstrapMock.mockResolvedValue({
      opt_accounts: ['ACC1 (Main)'],
      opt_assets: ['US0000000001 (Asset One)'],
      opt_trans_types: ['BUY (Buy)'],
      opt_asset: [],
      opt_gics: [],
      opt_region: [],
      opt_type: [],
      opt_source: [],
      db_region_map: {},
      type_logic_map: {},
    })

    listTransactionsMock.mockResolvedValue([
      {
        trade_date: '2026-01-01',
        account: 'ACC1',
        isin: 'US0000000001',
        name: 'Asset One',
        transaction_type: 'BUY',
        quantity: 10,
        settle_amount: 100,
        settle_currency: 'EUR',
        fx_rate: 1,
        amount_eur: 100,
        created_at: null,
        updated_at: null,
        internal_id: 'US0000000001_20260101_001',
      },
    ])

    getTransactionImportPreviewMock.mockResolvedValue({
      rows: [],
      missing_isins: [],
      existing_ids: [],
      duplicate_overlap_count: 0,
    })
    createAssetMock.mockResolvedValue({ isin: 'US9999999999' })
    createTransactionMock.mockResolvedValue({})
    importTransactionsBulkMock.mockResolvedValue({ saved_count: 1, skipped_overlap_count: 0 })
    deleteAllTransactionsMock.mockResolvedValue({ user_id: 'user-1', deleted: true })
    getTransactionImportSettingsMock.mockResolvedValue({ mapping_config: null })
    saveTransactionImportSettingsMock.mockResolvedValue({
      user_id: 'user-1',
      account_code: 'ACC1',
      saved: true,
    })

    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('loads and renders existing transactions', async () => {
    render(<TransactionsScreen session={session} onError={vi.fn()} />)

    expect(await screen.findByText('Transactions')).toBeInTheDocument()
    expect(await screen.findByText('US0000000001')).toBeInTheDocument()
  })

  it('creates a transaction from form values', async () => {
    render(<TransactionsScreen session={session} onError={vi.fn()} />)

    await screen.findByText('US0000000001')

    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '15.25' } })
    fireEvent.change(screen.getByLabelText('Settle Amount'), { target: { value: '250.5' } })

    fireEvent.click(screen.getByRole('button', { name: 'Save Transaction' }))

    await waitFor(() => {
      expect(createTransactionMock).toHaveBeenCalledTimes(1)
    })
  })

  it('filters transactions by search text', async () => {
    render(<TransactionsScreen session={session} onError={vi.fn()} />)

    await screen.findByText('US0000000001')

    fireEvent.change(screen.getByPlaceholderText('Search ISIN, name, type, internal id'), {
      target: { value: 'NO_MATCH' },
    })

    await waitFor(() => {
      expect(screen.queryByText('US0000000001')).not.toBeInTheDocument()
    })
  })

  it('shows missing ISIN warning after preview checks', async () => {
    getTransactionImportPreviewMock.mockResolvedValue({
      rows: [
        {
          user_id: 'user-1',
          account_code: 'ACC1',
          isin: 'US9999999999',
          date: '2026-01-10',
          transaction_type_code: 'BUY',
          quantity: 10,
          settle_amount: 100,
          settle_currency: 'EUR',
          settle_fxrate: 1,
          amount_eur: 100,
        },
      ],
      missing_isins: ['US9999999999'],
      existing_ids: [],
      duplicate_overlap_count: 0,
    })

    render(<TransactionsScreen session={session} onError={vi.fn()} />)
    await screen.findByText('Transactions')

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null
    expect(fileInput).not.toBeNull()
    const csvContent = [
      'isin,date,type,quantity,settle_amount,settle_currency',
      'US9999999999,2026-01-10,BUY,10,100,EUR',
    ].join('\n')
    const csv = new window.File([csvContent], 'import.csv', { type: 'text/csv' })

    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [csv] } })
    fireEvent.click(await screen.findByRole('button', { name: 'Build Preview' }))

    expect(await screen.findByText(/Missing ISINs in import/)).toBeInTheDocument()
  })

  it('provisions missing assets from warning action', async () => {
    getTransactionImportPreviewMock.mockResolvedValue({
      rows: [
        {
          user_id: 'user-1',
          account_code: 'ACC1',
          isin: 'US9999999999',
          date: '2026-01-10',
          transaction_type_code: 'BUY',
          quantity: 10,
          settle_amount: 100,
          settle_currency: 'EUR',
          settle_fxrate: 1,
          amount_eur: 100,
        },
      ],
      missing_isins: ['US9999999999'],
      existing_ids: [],
      duplicate_overlap_count: 0,
    })

    render(<TransactionsScreen session={session} onError={vi.fn()} />)
    await screen.findByText('Transactions')

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null
    expect(fileInput).not.toBeNull()
    const csvContent = [
      'isin,date,type,quantity,settle_amount,settle_currency',
      'US9999999999,2026-01-10,BUY,10,100,EUR',
    ].join('\n')
    const csv = new window.File([csvContent], 'import.csv', { type: 'text/csv' })

    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [csv] } })
    fireEvent.click(await screen.findByRole('button', { name: 'Build Preview' }))
    fireEvent.click(await screen.findByRole('button', { name: /Provision 1 Missing Assets/ }))

    await waitFor(() => {
      expect(createAssetMock).toHaveBeenCalledTimes(1)
    })
  })
})
