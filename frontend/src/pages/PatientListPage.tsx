// Clinician home page — patient list with search-on-click and pagination.
import { useState, useEffect, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { listPatients, type Patient } from '../api/patientApi'
import { useAuth } from '../context/AuthContext'

const PAGE_SIZE = 5

export default function PatientListPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Search: inputValue = what's typed; activeQuery = what's been submitted
  const [inputValue, setInputValue] = useState('')
  const [activeQuery, setActiveQuery] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    listPatients()
      .then(setPatients)
      .catch(() => setError('Failed to load patients.'))
      .finally(() => setLoading(false))
  }, [])

  function handleSearch() {
    setActiveQuery(inputValue)
    setPage(1)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleSearch()
  }

  const filtered = patients.filter(p =>
    activeQuery === '' ||
    p.name.toLowerCase().includes(activeQuery.toLowerCase()) ||
    (p.contact_email ?? '').toLowerCase().includes(activeQuery.toLowerCase())
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const displayed = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div style={s.page}>
      <header style={s.nav}>
        <span style={s.navTitle}>AI Diagnosis System</span>
        <div style={s.navRight}>
          <span style={s.navUser}>{user?.username} ({user?.role})</span>
          <button style={s.logoutBtn} onClick={logout}>Logout</button>
        </div>
      </header>

      <main style={s.main}>
        <h2 style={s.heading}>Patients</h2>

        <div style={s.toolbar}>
          <input
            style={s.searchInput}
            placeholder="Search by name or email…"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button style={s.searchBtn} onClick={handleSearch}>Search</button>
          <span style={s.hint}>{filtered.length} patient{filtered.length !== 1 ? 's' : ''}</span>
        </div>

        {error && <div style={s.errorBox}>{error}</div>}

        {loading ? (
          <p>Loading…</p>
        ) : displayed.length === 0 ? (
          <p style={{ color: '#7f8c8d' }}>No patients found.</p>
        ) : (
          <>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>Name</th>
                  <th style={s.th}>Date of Birth</th>
                  <th style={s.th}>Gender</th>
                  <th style={s.th}>Contact Email</th>
                  <th style={s.th}>Account</th>
                  <th style={s.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map(p => (
                  <tr key={p.id} style={s.tr}>
                    <td style={s.td}><strong>{p.name}</strong></td>
                    <td style={s.td}>{p.date_of_birth}</td>
                    <td style={s.td}>{p.gender}</td>
                    <td style={s.td}>{p.contact_email ?? '—'}</td>
                    <td style={s.td}>
                      {p.linked_user
                        ? <span style={s.linkedBadge}>✓ Linked</span>
                        : <span style={s.unlinkedBadge}>No account</span>}
                    </td>
                    <td style={s.td}>
                      <button style={s.detailBtn} onClick={() => navigate(`/patients/${p.id}`)}>
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <Pagination page={page} totalPages={totalPages} onChange={setPage} />
          </>
        )}
      </main>
    </div>
  )
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  if (totalPages <= 1) return null
  return (
    <div style={pg.row}>
      <button style={pg.btn} disabled={page === 1} onClick={() => onChange(page - 1)}>← Prev</button>
      <span style={pg.label}>Page {page} / {totalPages}</span>
      <button style={pg.btn} disabled={page === totalPages} onClick={() => onChange(page + 1)}>Next →</button>
    </div>
  )
}

const pg: Record<string, React.CSSProperties> = {
  row: { marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' },
  btn: { padding: '6px 14px', border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer', background: '#fff' },
  label: { color: '#7f8c8d', fontSize: '0.9rem' },
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f4f6f9', fontFamily: 'sans-serif' },
  nav: { background: '#2c3e50', color: '#fff', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  navTitle: { fontWeight: 700, fontSize: '1.1rem' },
  navRight: { display: 'flex', alignItems: 'center', gap: '12px' },
  navUser: { fontSize: '0.9rem', color: '#bdc3c7' },
  logoutBtn: { background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d', borderRadius: '6px', padding: '5px 12px', cursor: 'pointer' },
  main: { maxWidth: '960px', margin: '0 auto', padding: '24px' },
  heading: { marginTop: 0, color: '#2c3e50' },
  toolbar: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' },
  searchInput: { padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px', fontSize: '0.93rem', width: '260px' },
  searchBtn: { padding: '8px 16px', background: '#3498db', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 },
  hint: { color: '#7f8c8d', fontSize: '0.88rem', marginLeft: '4px' },
  errorBox: { background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb', borderRadius: '6px', padding: '10px 14px', marginBottom: '16px' },
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: '8px', overflow: 'hidden' },
  th: { padding: '11px 16px', background: '#ecf0f1', textAlign: 'left', fontWeight: 700, fontSize: '0.88rem', color: '#2c3e50', borderBottom: '1px solid #dce1e7' },
  tr: { borderBottom: '1px solid #ecf0f1' },
  td: { padding: '11px 16px', fontSize: '0.9rem', color: '#34495e', verticalAlign: 'middle' },
  detailBtn: { padding: '5px 14px', background: '#3498db', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem' },
  linkedBadge: { display: 'inline-block', padding: '2px 8px', borderRadius: '10px', background: '#d4edda', color: '#155724', fontSize: '0.82rem', fontWeight: 600 },
  unlinkedBadge: { display: 'inline-block', padding: '2px 8px', borderRadius: '10px', background: '#f0f0f0', color: '#7f8c8d', fontSize: '0.82rem' },
}
