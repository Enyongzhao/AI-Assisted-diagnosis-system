// design_doc §4.3 — GET /api/v1/diagnosis/
// Lists diagnosis tasks. Backend filters by role automatically:
//   Client → own records (no search bar, can change password)
//   Admin  → all records (with search bar)
//
// Client-specific behaviour:
//   - failed records are hidden
//   - auto-refreshes every 5 s while any record is still in progress
import { useState, useEffect, useRef, type KeyboardEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  listDiagnoses,
  type DiagnosisListItem,
  type DiagnosisStatus,
} from '../api/diagnosisApi'
import { changePassword } from '../api/authApi'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

const CLIENT_HIDDEN: DiagnosisStatus[] = ['failed']

const IN_PROGRESS: DiagnosisStatus[] = [
  'pending',
  'processing',
  'awaiting_doctor_input',
  'generating_pdf',
]

const POLL_INTERVAL_MS = 5000
const PAGE_SIZE = 5

export default function DiagnosisListPage() {
  const { user, logout } = useAuth()
  const isClient = user?.role === 'client'

  const [items, setItems] = useState<DiagnosisListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Search (admin only)
  const [inputValue, setInputValue] = useState('')
  const [activeQuery, setActiveQuery] = useState('')
  const [page, setPage] = useState(1)

  // Change password modal
  const [showPwModal, setShowPwModal] = useState(false)
  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwLoading, setPwLoading] = useState(false)

  function stopPoll() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  async function fetchAll(silent = false) {
    if (!silent) setLoading(true)
    try {
      const data = await listDiagnoses({ page_size: 500 })
      let results = data.results
      if (isClient) {
        results = results.filter(r => !CLIENT_HIDDEN.includes(r.status))
      }
      setItems(results)
      setError(null)

      if (isClient) {
        const hasInProgress = results.some(r => IN_PROGRESS.includes(r.status))
        if (hasInProgress && !intervalRef.current) {
          intervalRef.current = setInterval(() => fetchAll(true), POLL_INTERVAL_MS)
        }
        if (!hasInProgress) stopPoll()
      }
    } catch {
      setError('Failed to load diagnoses.')
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    return stopPoll
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSearch() {
    setActiveQuery(inputValue)
    setPage(1)
  }

  function handleSearchKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleSearch()
  }

  const filtered = items.filter(item =>
    activeQuery === '' ||
    item.patient_name.toLowerCase().includes(activeQuery.toLowerCase()) ||
    item.diagnosis_id.toLowerCase().includes(activeQuery.toLowerCase())
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const displayed = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // ── Change password ──────────────────────────────────────────────────────
  function openPwModal() {
    setPwCurrent('')
    setPwNew('')
    setPwConfirm('')
    setPwError(null)
    setPwSuccess(false)
    setShowPwModal(true)
  }

  async function handlePwSubmit(e: FormEvent) {
    e.preventDefault()
    if (pwNew !== pwConfirm) {
      setPwError('New passwords do not match.')
      return
    }
    if (pwNew.length < 6) {
      setPwError('New password must be at least 6 characters.')
      return
    }
    setPwError(null)
    setPwLoading(true)
    try {
      await changePassword(pwCurrent, pwNew)
      setPwSuccess(true)
      setTimeout(() => setShowPwModal(false), 1500)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to change password.'
      setPwError(msg)
    } finally {
      setPwLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <header style={styles.nav}>
        <span style={styles.navTitle}>AI Diagnosis System</span>
        <div style={styles.navRight}>
          <span style={styles.navUser}>{user?.username} ({user?.role})</span>
          {isClient && (
            <button style={styles.pwBtn} onClick={openPwModal}>Change Password</button>
          )}
          <button style={styles.logoutBtn} onClick={logout}>Logout</button>
        </div>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>
          {isClient ? 'My Reports' : 'Diagnosis Records'}
        </h2>

        {isClient && items.some(r => IN_PROGRESS.includes(r.status)) && (
          <div style={styles.infoBox}>
            Your report is being prepared. This page refreshes automatically every 5 seconds.
          </div>
        )}

        {/* Search toolbar — admin only */}
        {!isClient && (
          <div style={styles.toolbar}>
            <input
              style={styles.searchInput}
              placeholder="Search by patient name or ID…"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleSearchKeyDown}
            />
            <button style={styles.searchBtn} onClick={handleSearch}>Search</button>
            <span style={styles.hint}>{filtered.length} record{filtered.length !== 1 ? 's' : ''}</span>
          </div>
        )}

        {error && <div style={styles.errorBox}>{error}</div>}

        {loading ? (
          <p>Loading…</p>
        ) : displayed.length === 0 ? (
          <p style={{ color: '#7f8c8d' }}>
            {isClient ? 'No reports found.' : 'No diagnosis records found.'}
          </p>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr>
                  {!isClient && <th style={styles.th}>Diagnosis ID</th>}
                  <th style={styles.th}>Patient</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Submitted At</th>
                  <th style={styles.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map(item => (
                  <tr key={item.diagnosis_id} style={styles.tr}>
                    {!isClient && (
                      <td style={styles.td}>
                        <code style={{ fontSize: '0.8rem' }}>{item.diagnosis_id.slice(0, 8)}…</code>
                      </td>
                    )}
                    <td style={styles.td}>{item.patient_name}</td>
                    <td style={styles.td}><StatusBadge status={item.status} /></td>
                    <td style={styles.td}>{new Date(item.submitted_at).toLocaleString()}</td>
                    <td style={styles.td}>
                      <Link to={`/diagnosis/${item.diagnosis_id}`} style={styles.link}>View</Link>
                      {item.status === 'completed' && (
                        <Link to={`/diagnosis/${item.diagnosis_id}/report`} style={{ ...styles.link, marginLeft: '12px' }}>
                          PDF
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div style={styles.pagination}>
                <button style={styles.pageBtn} disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                <span style={styles.pageLabel}>Page {page} / {totalPages}</span>
                <button style={styles.pageBtn} disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
              </div>
            )}
          </>
        )}
      </main>

      {/* Change Password Modal */}
      {showPwModal && (
        <div style={styles.overlay} onClick={() => setShowPwModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>Change Password</h3>
            {pwSuccess ? (
              <div style={styles.successBox}>Password changed successfully!</div>
            ) : (
              <form onSubmit={handlePwSubmit} style={styles.modalForm}>
                {pwError && <div style={styles.errorBox}>{pwError}</div>}
                <label style={styles.label}>Current Password</label>
                <input
                  style={styles.input}
                  type="password"
                  required
                  value={pwCurrent}
                  onChange={e => setPwCurrent(e.target.value)}
                />
                <label style={styles.label}>New Password</label>
                <input
                  style={styles.input}
                  type="password"
                  required
                  value={pwNew}
                  onChange={e => setPwNew(e.target.value)}
                />
                <label style={styles.label}>Confirm New Password</label>
                <input
                  style={styles.input}
                  type="password"
                  required
                  value={pwConfirm}
                  onChange={e => setPwConfirm(e.target.value)}
                />
                <div style={styles.modalBtns}>
                  <button style={styles.saveBtn} type="submit" disabled={pwLoading}>
                    {pwLoading ? 'Saving…' : 'Confirm'}
                  </button>
                  <button style={styles.cancelBtn} type="button" onClick={() => setShowPwModal(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f4f6f9', fontFamily: 'sans-serif' },
  nav: {
    background: '#2c3e50', color: '#fff', padding: '12px 24px',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  navTitle: { fontWeight: 700, fontSize: '1.1rem' },
  navRight: { display: 'flex', alignItems: 'center', gap: '12px' },
  navUser: { fontSize: '0.9rem', color: '#bdc3c7' },
  pwBtn: {
    background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d',
    borderRadius: '6px', padding: '5px 12px', cursor: 'pointer', fontSize: '0.88rem',
  },
  logoutBtn: {
    background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d',
    borderRadius: '6px', padding: '5px 12px', cursor: 'pointer',
  },
  main: { maxWidth: '960px', margin: '0 auto', padding: '24px' },
  heading: { marginTop: 0, color: '#2c3e50' },
  infoBox: {
    background: '#eaf4fb', border: '1px solid #85c1e9', borderRadius: '6px',
    padding: '10px 16px', marginBottom: '16px', color: '#1a6fa1', fontSize: '0.9rem',
  },
  toolbar: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' },
  searchInput: { padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px', fontSize: '0.93rem', width: '280px' },
  searchBtn: { padding: '8px 16px', background: '#3498db', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 },
  hint: { color: '#7f8c8d', fontSize: '0.88rem', marginLeft: '4px' },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px', marginBottom: '12px',
  },
  successBox: {
    background: '#d4edda', color: '#155724', border: '1px solid #c3e6cb',
    borderRadius: '6px', padding: '12px 16px', textAlign: 'center', fontWeight: 600,
  },
  table: {
    width: '100%', borderCollapse: 'collapse', background: '#fff',
    borderRadius: '8px', overflow: 'hidden',
  },
  th: {
    padding: '12px 16px', background: '#ecf0f1', textAlign: 'left',
    fontWeight: 700, fontSize: '0.88rem', color: '#2c3e50', borderBottom: '1px solid #dce1e7',
  },
  tr: { borderBottom: '1px solid #ecf0f1' },
  td: { padding: '12px 16px', fontSize: '0.9rem', color: '#34495e', verticalAlign: 'middle' },
  link: { color: '#3498db', textDecoration: 'none', fontWeight: 600 },
  pagination: { marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' },
  pageBtn: { padding: '6px 14px', border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer', background: '#fff' },
  pageLabel: { color: '#7f8c8d', fontSize: '0.9rem' },
  // Modal
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
  },
  modal: {
    background: '#fff', borderRadius: '10px', padding: '28px 32px',
    width: '360px', boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
  },
  modalTitle: { margin: '0 0 20px', color: '#2c3e50', fontSize: '1.1rem' },
  modalForm: { display: 'flex', flexDirection: 'column', gap: '4px' },
  label: { fontWeight: 600, fontSize: '0.88rem', color: '#34495e', marginTop: '10px' },
  input: {
    padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px',
    fontSize: '0.93rem', width: '100%', boxSizing: 'border-box',
  },
  modalBtns: { display: 'flex', gap: '10px', marginTop: '18px' },
  saveBtn: {
    flex: 1, padding: '9px', background: '#3498db', color: '#fff',
    border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600,
  },
  cancelBtn: {
    flex: 1, padding: '9px', background: '#fff', color: '#7f8c8d',
    border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer',
  },
}
