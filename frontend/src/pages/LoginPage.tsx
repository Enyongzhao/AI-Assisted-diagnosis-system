// design_doc §4.1 — POST /api/v1/auth/login/
// Submits credentials, stores JWT tokens via AuthContext, then navigates to /.
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const loggedInUser = await login(username, password)
      // Admin goes to user-management page; everyone else to the diagnosis list.
      navigate(loggedInUser.role === 'admin' ? '/admin' : '/', { replace: true })
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>AI Diagnosis System</h1>
        <p style={styles.subtitle}>Sign in to your account</p>

        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>Username</label>
          <input
            style={styles.input}
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoFocus
          />

          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f4f6f9',
  },
  card: {
    background: '#fff',
    borderRadius: '10px',
    boxShadow: '0 2px 16px rgba(0,0,0,0.1)',
    padding: '2.5rem',
    width: '360px',
  },
  title: { margin: '0 0 4px', fontSize: '1.6rem', color: '#2c3e50' },
  subtitle: { margin: '0 0 1.5rem', color: '#7f8c8d', fontSize: '0.9rem' },
  form: { display: 'flex', flexDirection: 'column', gap: '10px' },
  label: { fontWeight: 600, fontSize: '0.9rem', color: '#34495e' },
  input: {
    padding: '9px 12px',
    border: '1px solid #dce1e7',
    borderRadius: '6px',
    fontSize: '0.95rem',
    outline: 'none',
  },
  button: {
    marginTop: '8px',
    padding: '10px',
    background: '#3498db',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  errorBox: {
    background: '#fdecea',
    color: '#c0392b',
    border: '1px solid #f5c6cb',
    borderRadius: '6px',
    padding: '10px 14px',
    marginBottom: '12px',
    fontSize: '0.9rem',
  },
}
