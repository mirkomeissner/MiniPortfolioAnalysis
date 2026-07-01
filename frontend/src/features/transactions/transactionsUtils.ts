import type { TransactionImportPreviewRow } from '../../shared/types/api'

export type ImportedRow = TransactionImportPreviewRow

export type DuplicateStrategy = 'allow' | 'skip'

export type CsvTable = {
  headers: string[]
  rows: Array<Record<string, string>>
}

export function extractCode(option: string): string {
  return option.split(' (')[0]
}

export function formatNumber(value: number | null, digits = 2): string {
  if (value === null || Number.isNaN(value)) {
    return '-'
  }

  return new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value)
}

function normalizedHeader(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')
}

export function findMappedHeader(headers: string[], aliases: string[]): string {
  const normalizedToOriginal = new Map(headers.map((header) => [normalizedHeader(header), header]))
  for (const alias of aliases) {
    const found = normalizedToOriginal.get(alias)
    if (found) {
      return found
    }
  }
  return headers[0] ?? ''
}

export function parseCsvTable(content: string): CsvTable {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  if (lines.length < 2) {
    throw new Error('CSV file must contain a header row and at least one data row.')
  }

  const headers = lines[0].split(',').map((cell) => cell.trim())
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(',').map((cell) => cell.trim())
    const record: Record<string, string> = {}
    headers.forEach((header, idx) => {
      record[header] = cells[idx] ?? ''
    })
    return record
  })

  return {
    headers,
    rows,
  }
}
