import { useMemo, useState } from 'react'
import { Navigate, NavLink, Route, Routes } from 'react-router-dom'

import { AccountsScreen } from '../features/accounts/AccountsScreen'
import { AssetsScreen } from '../features/assets/AssetsScreen'
import { LoginScreen } from '../features/auth/LoginScreen'
import { HoldingsScreen } from '../features/holdings/HoldingsScreen'
import { TransactionsScreen } from '../features/transactions/TransactionsScreen'
import { ApiError, login } from '../shared/api/client'
import type { SessionState } from '../shared/types/api'

function readStoredSession(): SessionState | null {
  const raw = window.localStorage.getItem('mini-portfolio-session')
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as SessionState
  } catch {
    window.localStorage.removeItem('mini-portfolio-session')
    return null
  }
}

export default function App() {
  const [session, setSession] = useState<SessionState | null>(() => readStoredSession())
  const [error, setError] = useState('')

  const onLogin = (next: SessionState) => {
    setSession(next)
    window.localStorage.setItem('mini-portfolio-session', JSON.stringify(next))
  }

  const logout = () => {
    setSession(null)
    window.localStorage.removeItem('mini-portfolio-session')
  }

  const navItems = useMemo(
    () => [
      { path: '/accounts', label: 'Accounts' },
      { path: '/assets', label: 'Assets' },
      { path: '/transactions', label: 'Transactions' },
      { path: '/holdings', label: 'Holdings' },
    ],
    [],
  )

  if (!session) {
    return (
      <main className="layout auth-layout">
        <LoginScreen
          onLogin={onLogin}
          onError={setError}
          login={async (payload) => {
            try {
              return await login(payload)
            } catch (apiError) {
              if (apiError instanceof ApiError) {
                throw new Error(`Login failed (${apiError.status}): ${apiError.message}`, {
                  cause: apiError,
                })
              }
              throw apiError
            }
          }}
        />
        {error ? <p className="error-banner">{error}</p> : null}
      </main>
    )
  }

  return (
    <div className="layout app-layout">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Signed in as</p>
          <h3>{session.username}</h3>
          <p className="muted">{session.email}</p>
        </div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.path} to={item.path} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button type="button" className="logout" onClick={logout}>
          Logout
        </button>
      </aside>

      <main className="content">
        {error ? <p className="error-banner">{error}</p> : null}
        <Routes>
          <Route path="/" element={<Navigate to="/accounts" replace />} />
          <Route path="/accounts" element={<AccountsScreen session={session} onError={setError} />} />
          <Route path="/assets" element={<AssetsScreen session={session} onError={setError} />} />
          <Route path="/transactions" element={<TransactionsScreen session={session} onError={setError} />} />
          <Route path="/holdings" element={<HoldingsScreen session={session} onError={setError} />} />
          <Route path="*" element={<Navigate to="/accounts" replace />} />
        </Routes>
      </main>
    </div>
  )
}
