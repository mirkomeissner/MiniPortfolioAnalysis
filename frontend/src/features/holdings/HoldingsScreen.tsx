import { useEffect, useMemo, useState } from 'react'

import { getHoldingsDateRange, listHoldings } from '../../shared/api/client'
import type { HoldingRecord, SessionState } from '../../shared/types/api'

type HoldingsScreenProps = {
  session: SessionState
  onError: (message: string) => void
}

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return '-'
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
}

export function HoldingsScreen({ session, onError }: HoldingsScreenProps) {
  const [rows, setRows] = useState<HoldingRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [holdingDate, setHoldingDate] = useState('')

  const loadDateAndData = async () => {
    setLoading(true)
    onError('')

    try {
      const range = await getHoldingsDateRange(session.userId, session.accessToken)
      const selectedDate = holdingDate || range.last_date
      setHoldingDate(selectedDate)

      const records = await listHoldings(session.userId, selectedDate, session.accessToken)
      setRows(records)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to load holdings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadDateAndData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.userId])

  const reloadForDate = async (nextDate: string) => {
    setHoldingDate(nextDate)
    setLoading(true)
    onError('')
    try {
      const records = await listHoldings(session.userId, nextDate, session.accessToken)
      setRows(records)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to load holdings')
    } finally {
      setLoading(false)
    }
  }

  const totalValuation = useMemo(
    () => rows.reduce((total, row) => total + (row.valuation_in_eur ?? 0), 0),
    [rows],
  )

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Holdings</h2>
        <div className="actions">
          <label className="compact-label">
            Date
            <input
              type="date"
              value={holdingDate}
              onChange={(event) => {
                void reloadForDate(event.target.value)
              }}
            />
          </label>
          <button type="button" onClick={() => void reloadForDate(holdingDate)} disabled={!holdingDate}>
            Refresh
          </button>
        </div>
      </header>

      <p className="summary">Total valuation (EUR): {formatNumber(totalValuation)}</p>

      {loading ? (
        <p>Loading holdings...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>ISIN</th>
              <th>Asset</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Valuation EUR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.account_code ?? 'unknown'}-${row.isin ?? 'unknown'}-${index}`}>
                <td>{row.account_code ?? '-'}</td>
                <td>{row.isin ?? '-'}</td>
                <td>{row.asset_name ?? '-'}</td>
                <td>{formatNumber(row.quantity)}</td>
                <td>
                  {formatNumber(row.price)} {row.price_currency ?? ''}
                </td>
                <td>{formatNumber(row.valuation_in_eur)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
