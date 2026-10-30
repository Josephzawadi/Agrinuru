import { useState, type FormEvent } from 'react'
import { ApiRequestError, authApi, type AuthUser } from '../../api/client'

type AuthMode = 'login' | 'register'

interface AuthPageProps {
  onAuthenticated: (user: AuthUser) => void
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setFieldErrors({})
    setNotice('')
    setSaving(true)

    try {
      if (mode === 'register') {
        await authApi.register({ username, email, password })
        setMode('login')
        setPassword('')
        setNotice('Account created. Sign in to continue.')
      } else {
        const user = await authApi.login({ username, password })
        onAuthenticated(user)
      }
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(requestError.message)
        setFieldErrors(requestError.fieldErrors)
      } else {
        setError('Could not reach the platform. Check your connection and try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <p className="eyebrow"><span /> AgriNuru account</p>
        <h1 id="auth-title">{mode === 'login' ? 'Welcome back.' : 'Create your account.'}</h1>
        <p className="auth-intro">
          {mode === 'login'
            ? 'Sign in to continue to the farm management workspace.'
            : 'Register as a farmer. Your account will not claim an existing farmer profile.'}
        </p>
        {notice && <p className="auth-notice" role="status">{notice}</p>}
        {error && <p className="auth-error" role="alert">{error}</p>}

        <form className="auth-form" onSubmit={submit}>
          <label>
            Username
            <input
              autoComplete="username"
              maxLength={150}
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
            {fieldErrors.username && <span className="auth-field-error">{fieldErrors.username}</span>}
          </label>

          {mode === 'register' && (
            <label>
              Email
              <input
                autoComplete="email"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
              {fieldErrors.email && <span className="auth-field-error">{fieldErrors.email}</span>}
            </label>
          )}

          <label>
            Password
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {fieldErrors.password && <span className="auth-field-error">{fieldErrors.password}</span>}
          </label>

          <button className="button-primary auth-submit" disabled={saving} type="submit">
            {saving ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          {mode === 'login' ? 'New to AgriNuru?' : 'Already registered?'}{' '}
          <button
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError('')
              setFieldErrors({})
              setNotice('')
            }}
            type="button"
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </section>
    </main>
  )
}
