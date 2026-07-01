import { useState } from 'react'

import type { SessionState } from '../../shared/types/api'

type LoginScreenProps = {
  onLogin: (session: SessionState) => void
  onError: (message: string) => void
  login: (payload: { email: string; password: string }) => Promise<{
    authenticated: boolean
    access_token: string | null
    user_id: string | null
    username: string | null
    email: string | null
  }>
}

export function LoginScreen({ onLogin, onError, login }: LoginScreenProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onError('')
    setLoading(true)

    try {
      const response = await login({ email, password })
      if (!response.authenticated || !response.user_id || !response.access_token) {
        onError('Login failed. Check credentials or approval status.')
        return
      }

      onLogin({
        accessToken: response.access_token,
        userId: response.user_id,
        username: response.username ?? response.email ?? response.user_id,
        email: response.email ?? email,
      })
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Unexpected login error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-card">
      <h1>Mini Portfolio React Frontend</h1>
      <p>Sign in against the FastAPI backend to open the first React screens.</p>

      <form onSubmit={submit} className="stack-sm">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            placeholder="you@example.com"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            placeholder="********"
          />
        </label>

        <button type="submit" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}
