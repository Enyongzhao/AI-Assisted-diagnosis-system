// design_doc §4.3 — GET /api/v1/diagnosis/
// Lists diagnosis tasks. Backend filters by role automatically:
//   Clinician → own submissions; Client → own records; Admin → all.
//
// Client-specific behaviour:
//   - failed records are hidden (client never sees a broken report)
//   - all in-progress statuses are displayed as "In Progress" (simplified)
//   - auto-refreshes every 5 s while any record is still in progress
import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listDiagnoses,
  type DiagnosisListItem,
  type DiagnosisStatus,
} from '../api/diagnosisApi'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

// Statuses the client never needs to see
const CLIENT_HIDDEN: DiagnosisStatus[] = ['failed']

// Statuses that mean "still being worked on" from the client's perspective
const IN_PROGRESS: DiagnosisStatus[] = [
  'pending',
  'processing',
  'awaiting_doctor_input',
  'generating_pdf',
]

const POLL_INTERVAL_MS = 5000

export default function DiagnosisListPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isClient = user?.role === 'client'

  const [items, setItems] = useState<DiagnosisListItem[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const PAGE_SIZE = 20

  function stopPoll() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  async function fetchPage(p: number, silent = false) {
    if (!silent) setLoading(true)
    try {
      const data = await listDiagnoses({ page: p, page_size: PAGE_SIZE })
      let results = data.results

      // Client: hide failed records entirely
      if (isClient) {
        results = results.filter(r => !CLIENT_HIDDEN.includes(r.status))
      }

      setItems(results)
      setCount(data.count)
      setError(null)

      // Auto-poll only while client has in-progress records
      if (isClient) {
        const hasInProgress = results.some(r => IN_PROGRESS.includes(r.status))
        if (hasInProgress && !intervalRef.current) {
          intervalRef.current = setInterval(() => fetchPage(p, true), POLL_INTERVAL_MS)
        }
        if (!hasInProgress) {
          stopPoll()
        }
      }
    } catch {
      setError('Failed to load diagnoses.')
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    fetchPage(page)
    return stopPoll
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const totalPages = Math.ceil(count / PAGE_SIZE)

  function renderStatus(item: DiagnosisListItem) {
    return <StatusBadge status={item.status} />
  }

  return (
    <div style={styles.page}>
      <header style={styles.nav}>
        <span style={styles.navTitle}>AI Diagnosis System</span>
        <div style={styles.navRight}>
          <span style={styles.navUser}>{user?.username} ({user?.role})</span>
          {user?.role === 'clinician' && (
            <button style={styles.newBtn} onClick={() => navigate('/diagnosis/submit')}>
              + New Diagnosis
            </button>
          )}
          <button style={styles.logoutBtn} onClick={logout}>Logout</button>
        </div>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>
          {isClient ? 'My Reports' : 'Diagnosis Records'}
        </h2>

        {/* Auto-refresh hint for client */}
        {isClient && items.some(r => IN_PROGRESS.includes(r.status)) && (
          <div style={styles.infoBox}>
            🔄 Your report is being prepared. This page refreshes automatically every 5 seconds.
          </div>
        )}

        {error && <div style={styles.errorBox}>{error}</div>}

        {loading ? (
          <p>Loading…</p>
        ) : items.length === 0 ? (
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
                {items.map(item => (
                  <tr key={item.diagnosis_id} style={styles.tr}>
                    {!isClient && (
                      <td style={styles.td}>
                        <code style={{ fontSize: '0.8rem' }}>{item.diagnosis_id.slice(0, 8)}…</code>
                      </td>
                    )}
                    <td style={styles.td}>{item.patient_name}</td>
                    <td style={styles.td}>{renderStatus(item)}</td>
                    <td style={styles.td}>{new Date(item.submitted_at).toLocaleString()}</td>
                    <td style={styles.td}>
                      <Link to={`/diagnosis/${item.diagnosis_id}`} style={styles.link}>
                        View
                      </Link>
                      {item.status === 'completed' && (
                        <Link
                          to={`/diagnosis/${item.diagnosis_id}/report`}
                          style={{ ...styles.link, marginLeft: '12px' }}
                        >
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
                <button
                  style={styles.pageBtn}
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  ← Prev
                </button>
                <span style={{ margin: '0 12px' }}>Page {page} / {totalPages}</span>
                <button
                  style={styles.pageBtn}
                  disabled={page === totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </main>
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
  newBtn: {
    background: '#27ae60', color: '#fff', border: 'none',
    borderRadius: '6px', padding: '6px 14px', cursor: 'pointer', fontWeight: 600,
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
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px', marginBottom: '16px',
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
  pagination: { marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  pageBtn: {
    padding: '6px 14px', border: '1px solid #dce1e7',
    borderRadius: '6px', cursor: 'pointer', background: '#fff',
  },
}
