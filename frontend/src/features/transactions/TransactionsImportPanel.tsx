import type { ChangeEvent, Dispatch, SetStateAction } from 'react'

import type { TransactionImportMappingConfig } from '../../shared/types/api'
import type { CsvTable, DuplicateStrategy, ImportedRow } from './transactionsUtils'

type TransactionsImportPanelProps = {
  accountOptions: string[]
  importAccountSelection: string
  setImportAccountSelection: (value: string) => void
  saveCurrentImportMapping: () => Promise<void>
  savingMapping: boolean
  handleCsvFile: (event: ChangeEvent<HTMLInputElement>) => Promise<void>
  refreshImportPreview: () => Promise<void>
  csvTable: CsvTable | null
  checkingImport: boolean
  handleBulkImport: () => Promise<void>
  importing: boolean
  importRowsAfterStrategy: ImportedRow[]
  importMapping: TransactionImportMappingConfig
  setImportMapping: Dispatch<SetStateAction<TransactionImportMappingConfig>>
  importedRowsPreview: ImportedRow[]
  missingIsins: string[]
  provisionMissingAssets: () => Promise<void>
  provisioningAssets: boolean
  existingImportIds: string[]
  duplicatePreviewCount: number
  duplicateStrategy: DuplicateStrategy
  setDuplicateStrategy: (value: DuplicateStrategy) => void
}

export function TransactionsImportPanel({
  accountOptions,
  importAccountSelection,
  setImportAccountSelection,
  saveCurrentImportMapping,
  savingMapping,
  handleCsvFile,
  refreshImportPreview,
  csvTable,
  checkingImport,
  handleBulkImport,
  importing,
  importRowsAfterStrategy,
  importMapping,
  setImportMapping,
  importedRowsPreview,
  missingIsins,
  provisionMissingAssets,
  provisioningAssets,
  existingImportIds,
  duplicatePreviewCount,
  duplicateStrategy,
  setDuplicateStrategy,
}: TransactionsImportPanelProps) {
  return (
    <section className="import-section">
      <h3>CSV Import (mapped)</h3>
      <p className="summary">
        Upload CSV, map the required fields, preview rows, then import in bulk. Mapping is saved per account.
      </p>
      <div className="filter-row">
        <select value={importAccountSelection} onChange={(event) => setImportAccountSelection(event.target.value)}>
          {accountOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => void saveCurrentImportMapping()} disabled={savingMapping}>
          {savingMapping ? 'Saving Mapping...' : 'Save Mapping'}
        </button>
      </div>
      <div className="actions">
        <input type="file" accept=".csv,text/csv" onChange={(event) => void handleCsvFile(event)} />
        <button type="button" onClick={() => void refreshImportPreview()} disabled={!csvTable || checkingImport}>
          {checkingImport ? 'Checking...' : 'Build Preview'}
        </button>
        <button type="button" onClick={() => void handleBulkImport()} disabled={importing || importRowsAfterStrategy.length === 0}>
          {importing ? 'Importing...' : `Import ${importRowsAfterStrategy.length} Rows`}
        </button>
      </div>

      {csvTable ? (
        <div className="mapping-grid">
          <label>
            ISIN Column
            <select
              value={importMapping.map_isin ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_isin: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date Column
            <select
              value={importMapping.map_date ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_date: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Type Column
            <select
              value={importMapping.map_type ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_type: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantity Column
            <select
              value={importMapping.map_quantity ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_quantity: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Settle Amount Column
            <select
              value={importMapping.map_settle_amount ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_settle_amount: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Settle Currency Column
            <select
              value={importMapping.map_settle_currency ?? ''}
              onChange={(event) => setImportMapping((prev) => ({ ...prev, map_settle_currency: event.target.value }))}
            >
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            FX Rate Column (optional)
            <select
              value={importMapping.map_settle_fxrate ?? ''}
              onChange={(event) =>
                setImportMapping((prev) => ({
                  ...prev,
                  map_settle_fxrate: event.target.value || undefined,
                }))
              }
            >
              <option value="">(Not in CSV)</option>
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
          <label>
            Amount EUR Column (optional)
            <select
              value={importMapping.map_amount_eur ?? ''}
              onChange={(event) =>
                setImportMapping((prev) => ({
                  ...prev,
                  map_amount_eur: event.target.value || undefined,
                }))
              }
            >
              <option value="">(Not in CSV)</option>
              {csvTable.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      {importedRowsPreview.length > 0 ? (
        <p className="summary">
          Preview loaded: {importedRowsPreview.length} rows. After duplicate strategy: {importRowsAfterStrategy.length}
          rows.
        </p>
      ) : null}

      {missingIsins.length > 0 ? (
        <div className="warning-actions">
          <p className="warning-banner">Missing ISINs in import: {missingIsins.join(', ')}</p>
          <button type="button" onClick={() => void provisionMissingAssets()} disabled={provisioningAssets}>
            {provisioningAssets ? 'Provisioning...' : `Provision ${missingIsins.length} Missing Assets`}
          </button>
        </div>
      ) : null}

      {existingImportIds.length > 0 ? (
        <div className="warning-actions">
          <p className="warning-banner">
            Existing transactions found ({existingImportIds.length} ids; {duplicatePreviewCount} import rows overlap by
            ISIN/date).
          </p>
          <label className="compact-label">
            Duplicate Strategy
            <select value={duplicateStrategy} onChange={(event) => setDuplicateStrategy(event.target.value as DuplicateStrategy)}>
              <option value="allow">Import all rows (allow overlaps)</option>
              <option value="skip">Skip overlapping ISIN/date rows</option>
            </select>
          </label>
        </div>
      ) : null}
    </section>
  )
}
