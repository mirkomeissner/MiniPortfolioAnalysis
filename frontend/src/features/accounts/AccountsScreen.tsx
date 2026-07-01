import { useEffect, useState } from 'react'

import type { AccountRecord, SessionState } from '../../shared/types/api'
import { createAccount, listAccounts, updateAccount } from '../../shared/api/client'

type AccountsScreenProps = {
  session: SessionState
  onError: (message: string) => void
}

export function AccountsScreen({ session, onError }: AccountsScreenProps) {
  const [rows, setRows] = useState<AccountRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [accountCode, setAccountCode] = useState('')
  const [description, setDescription] = useState('')

  const load = async () => {
    setLoading(true)
    onError('')
    try {
      const records = await listAccounts(session.userId, session.accessToken)
      setRows(records)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to load accounts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.userId])

  const create = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onError('')
    try {
      await createAccount(session.userId, accountCode.trim(), description.trim(), session.accessToken)
      setAccountCode('')
      setDescription('')
      await load()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to create account')
    }
  }

  const editDescription = async (row: AccountRecord) => {
    const next = window.prompt(`Update description for ${row.account_code}`, row.description ?? '')
    if (next === null) {
      return
    }

    try {
      await updateAccount(session.userId, row.account_code, next, session.accessToken)
      await load()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to update account')
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Accounts</h2>
        <button type="button" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      <form onSubmit={create} className="inline-form">
        <input
          value={accountCode}
          onChange={(event) => setAccountCode(event.target.value)}
          placeholder="Account code"
          required
        />
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Description"
          required
        />
        <button type="submit">Create</button>
      </form>

      {loading ? (
        <p>Loading accounts...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Description</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.account_code}>
                <td>{row.account_code}</td>
                <td>{row.description ?? '-'}</td>
                <td>
                  <button type="button" onClick={() => void editDescription(row)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
