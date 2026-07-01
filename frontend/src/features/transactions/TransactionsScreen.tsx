import { useEffect, useMemo, useState } from 'react'

import {
  createAsset,
  createTransaction,
  deleteAllTransactions,
  getReferenceBootstrap,
  importTransactionsBulk,
  getTransactionImportPreview,
  getTransactionImportSettings,
  listTransactions,
  saveTransactionImportSettings,
} from '../../shared/api/client'
import type { SessionState, TransactionImportMappingConfig, TransactionRecord } from '../../shared/types/api'
import { TransactionsDataTable } from './TransactionsDataTable'
import { TransactionsImportPanel } from './TransactionsImportPanel'
import {
  extractCode,
  findMappedHeader,
  formatNumber,
  parseCsvTable,
  type CsvTable,
  type DuplicateStrategy,
  type ImportedRow,
} from './transactionsUtils'

type TransactionsScreenProps = {
  session: SessionState
  onError: (message: string) => void
}

export function TransactionsScreen({ session, onError }: TransactionsScreenProps) {
  const [rows, setRows] = useState<TransactionRecord[]>([])
  const [loading, setLoading] = useState(true)

  const [accountOptions, setAccountOptions] = useState<string[]>([])
  const [assetOptions, setAssetOptions] = useState<string[]>([])
  const [transactionTypeOptions, setTransactionTypeOptions] = useState<string[]>([])

  const [accountSelection, setAccountSelection] = useState('')
  const [assetSelection, setAssetSelection] = useState('')
  const [typeSelection, setTypeSelection] = useState('')
  const [tradeDate, setTradeDate] = useState(new Date().toISOString().slice(0, 10))
  const [settleCurrency, setSettleCurrency] = useState('EUR')
  const [quantity, setQuantity] = useState<number>(0)
  const [settleAmount, setSettleAmount] = useState<number>(0)
  const [fxRate, setFxRate] = useState<number>(1)
  const [saving, setSaving] = useState(false)
  const [csvTable, setCsvTable] = useState<CsvTable | null>(null)
  const [csvContent, setCsvContent] = useState<string | null>(null)
  const [importMapping, setImportMapping] = useState<TransactionImportMappingConfig>({})
  const [importAccountSelection, setImportAccountSelection] = useState('')
  const [importedRowsPreview, setImportedRowsPreview] = useState<ImportedRow[]>([])
  const [importing, setImporting] = useState(false)
  const [savingMapping, setSavingMapping] = useState(false)
  const [checkingImport, setCheckingImport] = useState(false)
  const [provisioningAssets, setProvisioningAssets] = useState(false)
  const [missingIsins, setMissingIsins] = useState<string[]>([])
  const [existingImportIds, setExistingImportIds] = useState<string[]>([])
  const [duplicateOverlapCount, setDuplicateOverlapCount] = useState(0)
  const [duplicateStrategy, setDuplicateStrategy] = useState<DuplicateStrategy>('allow')

  const [searchText, setSearchText] = useState('')
  const [accountFilter, setAccountFilter] = useState('ALL')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const isEur = settleCurrency === 'EUR'

  const amountEur = useMemo(() => {
    if (isEur) {
      return settleAmount
    }

    if (!fxRate) {
      return 0
    }

    return settleAmount / fxRate
  }, [fxRate, isEur, settleAmount])

  const filteredRows = useMemo(() => {
    const normalizedSearch = searchText.trim().toLowerCase()
    return rows.filter((row) => {
      if (accountFilter !== 'ALL' && row.account !== accountFilter) {
        return false
      }

      if (fromDate && row.trade_date && row.trade_date < fromDate) {
        return false
      }
      if (toDate && row.trade_date && row.trade_date > toDate) {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      const text = [row.isin, row.name, row.transaction_type, row.internal_id]
        .filter((value): value is string => Boolean(value))
        .join(' ')
        .toLowerCase()

      return text.includes(normalizedSearch)
    })
  }, [accountFilter, fromDate, rows, searchText, toDate])

  const duplicatePairSet = useMemo(() => {
    return new Set(
      existingImportIds
        .map((id) => {
          const parts = id.split('_')
          if (parts.length < 2) {
            return null
          }
          const dateToken = parts[1]
          if (dateToken.length !== 8) {
            return null
          }
          const normalizedDate = `${dateToken.slice(0, 4)}-${dateToken.slice(4, 6)}-${dateToken.slice(6, 8)}`
          return `${parts[0]}|${normalizedDate}`
        })
        .filter((value): value is string => Boolean(value)),
    )
  }, [existingImportIds])

  const duplicatePreviewCount = useMemo(() => {
    if (duplicateOverlapCount > 0) {
      return duplicateOverlapCount
    }
    return importedRowsPreview.filter((row) => duplicatePairSet.has(`${row.isin}|${row.date}`)).length
  }, [duplicateOverlapCount, duplicatePairSet, importedRowsPreview])

  const importRowsAfterStrategy = useMemo(() => {
    if (duplicateStrategy === 'allow') {
      return importedRowsPreview
    }

    return importedRowsPreview.filter((row) => !duplicatePairSet.has(`${row.isin}|${row.date}`))
  }, [duplicatePairSet, duplicateStrategy, importedRowsPreview])

  const load = async () => {
    setLoading(true)
    onError('')

    try {
      const [reference, transactions] = await Promise.all([
        getReferenceBootstrap(session.userId, session.accessToken),
        listTransactions(session.userId, session.accessToken),
      ])

      setRows(transactions)
      setAccountOptions(reference.opt_accounts)
      setAssetOptions(reference.opt_assets)
      setTransactionTypeOptions(reference.opt_trans_types)

      if (!accountSelection && reference.opt_accounts.length > 0) {
        setAccountSelection(reference.opt_accounts[0])
      }
      if (!assetSelection && reference.opt_assets.length > 0) {
        setAssetSelection(reference.opt_assets[0])
      }
      if (!typeSelection && reference.opt_trans_types.length > 0) {
        setTypeSelection(reference.opt_trans_types[0])
      }
      if (!importAccountSelection && reference.opt_accounts.length > 0) {
        setImportAccountSelection(reference.opt_accounts[0])
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.userId])

  useEffect(() => {
    const loadImportSettings = async () => {
      const importAccountCode = extractCode(importAccountSelection)
      if (!importAccountCode) {
        return
      }

      try {
        const response = await getTransactionImportSettings(
          session.userId,
          importAccountCode,
          session.accessToken,
        )
        setImportMapping(response.mapping_config ?? {})
      } catch {
        setImportMapping({})
      }
    }

    void loadImportSettings()
  }, [importAccountSelection, session.accessToken, session.userId])

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!accountSelection || !assetSelection || !typeSelection) {
      onError('Please choose account, asset, and transaction type before saving.')
      return
    }

    if (!isEur && fxRate <= 0) {
      onError('FX rate must be greater than 0 for non-EUR transactions.')
      return
    }

    setSaving(true)
    onError('')

    try {
      const cleanIsin = extractCode(assetSelection)

      await createTransaction(
        {
          user_id: session.userId,
          account_code: extractCode(accountSelection),
          isin: cleanIsin,
          date: tradeDate,
          transaction_type_code: extractCode(typeSelection),
          quantity,
          settle_amount: settleAmount,
          settle_currency: settleCurrency,
          settle_fxrate: isEur ? 1 : fxRate,
          amount_eur: amountEur,
        },
        session.accessToken,
      )

      await load()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to create transaction')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAll = async () => {
    const confirmed = window.confirm(
      'Delete all transactions for this user? This operation also invalidates holdings snapshots.',
    )
    if (!confirmed) {
      return
    }

    onError('')
    try {
      await deleteAllTransactions(session.userId, session.accessToken)
      await load()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to delete transactions')
    }
  }

  const handleCsvFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    onError('')
    try {
      const content = await file.text()
      const parsedTable = parseCsvTable(content)
      setCsvTable(parsedTable)
      setCsvContent(content)
      setMissingIsins([])
      setExistingImportIds([])
      setDuplicateOverlapCount(0)
      setDuplicateStrategy('allow')

      setImportMapping((previous) => ({
        map_isin: previous.map_isin ?? findMappedHeader(parsedTable.headers, ['isin']),
        map_date: previous.map_date ?? findMappedHeader(parsedTable.headers, ['date', 'trade_date', 'transaction_date']),
        map_type: previous.map_type ?? findMappedHeader(parsedTable.headers, ['type', 'transaction_type', 'transaction_type_code']),
        map_quantity: previous.map_quantity ?? findMappedHeader(parsedTable.headers, ['quantity', 'qty']),
        map_settle_amount:
          previous.map_settle_amount ?? findMappedHeader(parsedTable.headers, ['settle_amount', 'settlement_amount', 'amount']),
        map_settle_currency:
          previous.map_settle_currency ?? findMappedHeader(parsedTable.headers, ['settle_currency', 'settlement_currency', 'currency']),
        map_settle_fxrate: previous.map_settle_fxrate,
        map_amount_eur: previous.map_amount_eur,
      }))
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to parse CSV file')
      setCsvTable(null)
      setCsvContent(null)
      setImportedRowsPreview([])
    }
  }

  const refreshImportPreview = async () => {
    if (!csvTable || !csvContent) {
      setImportedRowsPreview([])
      return
    }

    setCheckingImport(true)
    try {
      const importAccountCode = extractCode(importAccountSelection)
      if (!importAccountCode) {
        throw new Error('Please select an account for import.')
      }

      const preview = await getTransactionImportPreview(
        {
          user_id: session.userId,
          account_code: importAccountCode,
          csv_content: csvContent,
          mapping_config: importMapping,
        },
        session.accessToken,
      )

      setImportedRowsPreview(preview.rows)
      setMissingIsins(preview.missing_isins)
      setExistingImportIds(preview.existing_ids)
      setDuplicateOverlapCount(preview.duplicate_overlap_count)
      onError('')
    } catch (error) {
      setImportedRowsPreview([])
      setMissingIsins([])
      setExistingImportIds([])
      setDuplicateOverlapCount(0)
      onError(error instanceof Error ? error.message : 'Failed to build import preview')
    } finally {
      setCheckingImport(false)
    }
  }

  const saveCurrentImportMapping = async () => {
    const importAccountCode = extractCode(importAccountSelection)
    if (!importAccountCode) {
      onError('Please select an import account before saving mapping.')
      return
    }

    setSavingMapping(true)
    onError('')
    try {
      await saveTransactionImportSettings(
        session.userId,
        importAccountCode,
        importMapping,
        session.accessToken,
      )
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to save import mapping')
    } finally {
      setSavingMapping(false)
    }
  }

  const handleBulkImport = async () => {
    if (importedRowsPreview.length === 0) {
      onError('Create a valid import preview first.')
      return
    }

    if (missingIsins.length > 0) {
      onError('Import blocked: missing ISINs must be provisioned before import.')
      return
    }

    if (importRowsAfterStrategy.length === 0) {
      onError('Import blocked: no rows remain after applying duplicate strategy.')
      return
    }

    setImporting(true)
    onError('')
    try {
      await importTransactionsBulk(
        {
          user_id: session.userId,
          rows: importRowsAfterStrategy,
          duplicate_strategy: duplicateStrategy,
        },
        session.accessToken,
      )
      setImportedRowsPreview([])
      setCsvTable(null)
      setCsvContent(null)
      setDuplicateOverlapCount(0)
      await load()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to import transactions')
    } finally {
      setImporting(false)
    }
  }

  const provisionMissingAssets = async () => {
    if (missingIsins.length === 0) {
      return
    }

    setProvisioningAssets(true)
    onError('')
    try {
      const minDateByIsin = new Map<string, string>()
      for (const row of importedRowsPreview) {
        const existing = minDateByIsin.get(row.isin)
        if (!existing || row.date < existing) {
          minDateByIsin.set(row.isin, row.date)
        }
      }

      await Promise.all(
        missingIsins.map(async (isin) => {
          await createAsset(
            {
              isin,
              name: isin,
              price_start_date: minDateByIsin.get(isin) ?? null,
              created_by: session.userId,
            },
            session.userId,
            session.accessToken,
          )
        }),
      )

      await refreshImportPreview()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to provision missing assets')
    } finally {
      setProvisioningAssets(false)
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Transactions</h2>
        <div className="actions">
          <button type="button" onClick={() => void load()}>
            Refresh
          </button>
          <button type="button" className="danger" onClick={() => void handleDeleteAll()}>
            Delete All
          </button>
        </div>
      </header>

      <section className="filter-row">
        <input
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="Search ISIN, name, type, internal id"
        />
        <select value={accountFilter} onChange={(event) => setAccountFilter(event.target.value)}>
          <option value="ALL">All Accounts</option>
          {Array.from(new Set(rows.map((row) => row.account).filter((value): value is string => Boolean(value)))).map(
            (account) => (
              <option key={account} value={account}>
                {account}
              </option>
            ),
          )}
        </select>
        <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
        <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
      </section>

      <form onSubmit={handleCreate} className="transaction-form">
        <label>
          Account
          <select
            value={accountSelection}
            onChange={(event) => setAccountSelection(event.target.value)}
            required
          >
            {accountOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          Asset (ISIN)
          <select value={assetSelection} onChange={(event) => setAssetSelection(event.target.value)} required>
            {assetOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          Type
          <select value={typeSelection} onChange={(event) => setTypeSelection(event.target.value)} required>
            {transactionTypeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          Trade Date
          <input type="date" value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} required />
        </label>

        <label>
          Quantity
          <input
            type="number"
            step="0.0001"
            value={quantity}
            onChange={(event) => setQuantity(Number(event.target.value))}
            required
          />
        </label>

        <label>
          Settle Amount
          <input
            type="number"
            step="0.01"
            value={settleAmount}
            onChange={(event) => setSettleAmount(Number(event.target.value))}
            required
          />
        </label>

        <label>
          Currency
          <select
            value={settleCurrency}
            onChange={(event) => {
              const nextCurrency = event.target.value
              setSettleCurrency(nextCurrency)
              if (nextCurrency === 'EUR') {
                setFxRate(1)
              }
            }}
          >
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
            <option value="CHF">CHF</option>
            <option value="GBP">GBP</option>
            <option value="JPY">JPY</option>
            <option value="CAD">CAD</option>
          </select>
        </label>

        <label>
          FX Rate
          <input
            type="number"
            step="0.000001"
            value={isEur ? 1 : fxRate}
            onChange={(event) => setFxRate(Number(event.target.value))}
            disabled={isEur}
            required
          />
        </label>

        <div className="transaction-summary">Amount (EUR): {formatNumber(amountEur, 2)}</div>

        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save Transaction'}
        </button>
      </form>

      <TransactionsImportPanel
        accountOptions={accountOptions}
        importAccountSelection={importAccountSelection}
        setImportAccountSelection={setImportAccountSelection}
        saveCurrentImportMapping={saveCurrentImportMapping}
        savingMapping={savingMapping}
        handleCsvFile={handleCsvFile}
        refreshImportPreview={refreshImportPreview}
        csvTable={csvTable}
        checkingImport={checkingImport}
        handleBulkImport={handleBulkImport}
        importing={importing}
        importRowsAfterStrategy={importRowsAfterStrategy}
        importMapping={importMapping}
        setImportMapping={setImportMapping}
        importedRowsPreview={importedRowsPreview}
        missingIsins={missingIsins}
        provisionMissingAssets={provisionMissingAssets}
        provisioningAssets={provisioningAssets}
        existingImportIds={existingImportIds}
        duplicatePreviewCount={duplicatePreviewCount}
        duplicateStrategy={duplicateStrategy}
        setDuplicateStrategy={setDuplicateStrategy}
      />

      <TransactionsDataTable loading={loading} rows={filteredRows} />
    </section>
  )
}
