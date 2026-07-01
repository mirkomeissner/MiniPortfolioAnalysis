import { useEffect, useMemo, useState } from 'react'

import { listAssets } from '../../shared/api/client'
import type { AssetRecord, SessionState } from '../../shared/types/api'

type AssetsScreenProps = {
  session: SessionState
  onError: (message: string) => void
}

export function AssetsScreen({ session, onError }: AssetsScreenProps) {
  const [rows, setRows] = useState<AssetRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  const load = async () => {
    setLoading(true)
    onError('')
    try {
      const records = await listAssets(session.accessToken, session.userId)
      setRows(records)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return rows
    }

    return rows.filter((row) => {
      const blob = [row.isin, row.name, row.ticker, row.asset_class, row.region].join(' ').toLowerCase()
      return blob.includes(normalized)
    })
  }, [query, rows])

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Assets</h2>
        <div className="actions">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter by ISIN, name, ticker..."
          />
          <button type="button" onClick={() => void load()}>
            Refresh
          </button>
        </div>
      </header>

      {loading ? (
        <p>Loading assets...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ISIN</th>
              <th>Name</th>
              <th>Ticker</th>
              <th>Asset Class</th>
              <th>Region</th>
              <th>Closed On</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              <tr key={`${row.isin ?? 'unknown'}-${row.ticker ?? 'unknown'}`}>
                <td>{row.isin ?? '-'}</td>
                <td>{row.name ?? '-'}</td>
                <td>{row.ticker ?? '-'}</td>
                <td>{row.asset_class ?? '-'}</td>
                <td>{row.region ?? '-'}</td>
                <td>{row.closed_on ?? 'Open'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
