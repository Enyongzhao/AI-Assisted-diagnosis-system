// Per-patient diagnosis records for clinician.
// "+ New Diagnosis" button sits on the right of the "Diagnosis Records" heading row.
import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getPatient, type Patient } from '../api/patientApi'
import { listDiagnoses, type DiagnosisListItem } from '../api/diagnosisApi'
import StatusBadge from '../components/StatusBadge'

const PAGE_SIZE = 5

export default function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()

  const [patient, setPatient] = useState<Patient | null>(null)
  const [diagnoses, setDiagnoses] = useState<DiagnosisListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [diagPage, setDiagPage] = useState(1)

  useEffect(() => {
    if (!patientId) return
    const id = parseInt(patientId)

    Promise.all([
      getPatient(id),
      listDiagnoses({ patient_id: id, page_size: 100 }),
    ])
      .then(([pat, diag]) => {
        setPatient(pat)
        setDiagnoses(diag.results)
      })
      .catch(() => setError('Failed to load patient data.'))
      .finally(() => setLoading(false))
  }, [patientId])

  if (loading) return <Shell onBack={() => navigate('/')}><p style={{ padding: '1rem' }}>Loading…</p></Shell>
  if (error || !patient) return <Shell onBack={() => navigate('/')}><div style={s.errorBox}>{error ?? 'Patient not found.'}</div></Shell>

  return (
    <Shell onBack={() => navigate('/')}>
      {/* Patient info card */}
      <div style={s.infoCard}>
        <div style={s.infoGrid}>
          <InfoItem label="Name" value={patient.name} />
          <InfoItem label="Date of Birth" value={patient.date_of_birth} />
          <InfoItem label="Gender" value={patient.gender} />
          <InfoItem label="Contact Email" value={patient.contact_email ?? '—'} />
          <InfoItem
            label="Client Account"
            value={patient.linked_user ? '✓ Linked' : 'No account'}
            valueStyle={{ color: patient.linked_user ? '#27ae60' : '#7f8c8d' }}
          />
        </div>
      </div>

      {/* Diagnosis Records section */}
      <div style={s.sectionHeader}>
        <h3 style={s.sectionTitle}>Diagnosis Records</h3>
        <button
          style={s.newBtn}
          onClick={() => navigate(`/patients/${patientId}/diagnosis/submit`)}
        >
          + New Diagnosis
        </button>
      </div>

      {diagnoses.length === 0 ? (
        <p style={{ color: '#7f8c8d' }}>No diagnosis records yet.</p>
      ) : (() => {
        const totalPages = Math.max(1, Math.ceil(diagnoses.length / PAGE_SIZE))
        const displayed = diagnoses.slice((diagPage - 1) * PAGE_SIZE, diagPage * PAGE_SIZE)
        return (
          <>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>Diagnosis ID</th>
                  <th style={s.th}>Status</th>
                  <th style={s.th}>Submitted At</th>
                  <th style={s.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map(d => (
                  <tr key={d.diagnosis_id} style={s.tr}>
                    <td style={s.td}>
                      <code style={{ fontSize: '0.8rem' }}>{d.diagnosis_id.slice(0, 8)}…</code>
                    </td>
                    <td style={s.td}><StatusBadge status={d.status} /></td>
                    <td style={s.td}>{new Date(d.submitted_at).toLocaleString()}</td>
                    <td style={s.td}>
                      <Link to={`/diagnosis/${d.diagnosis_id}`} style={s.link}>View</Link>
                      {d.status === 'completed' && (
                        <Link to={`/diagnosis/${d.diagnosis_id}/report`} style={{ ...s.link, marginLeft: '12px' }}>
                          PDF
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPages > 1 && (
              <div style={s.pagination}>
                <button style={s.pageBtn} disabled={diagPage === 1} onClick={() => setDiagPage(p => p - 1)}>← Prev</button>
                <span style={s.pageLabel}>Page {diagPage} / {totalPages}</span>
                <button style={s.pageBtn} disabled={diagPage === totalPages} onClick={() => setDiagPage(p => p + 1)}>Next →</button>
              </div>
            )}
          </>
        )
      })()}
    </Shell>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function Shell({ children, onBack }: { children: React.ReactNode; onBack: () => void }) {
  return (
    <div style={{ minHeight: '100vh', background: '#f4f6f9', fontFamily: 'sans-serif' }}>
      <header style={s.nav}>
        <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>AI Diagnosis System</span>
        <button style={s.backBtn} onClick={onBack}>← Back to Patients</button>
      </header>
      <main style={s.main}>{children}</main>
    </div>
  )
}

function InfoItem({ label, value, valueStyle }: { label: string; value: string; valueStyle?: React.CSSProperties }) {
  return (
    <div>
      <div style={s.infoLabel}>{label}</div>
      <div style={{ ...s.infoValue, ...valueStyle }}>{value}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  nav: {
    background: '#2c3e50', color: '#fff', padding: '12px 24px',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  backBtn: {
    background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d',
    borderRadius: '6px', padding: '5px 12px', cursor: 'pointer',
  },
  main: { maxWidth: '900px', margin: '0 auto', padding: '24px' },
  infoCard: {
    background: '#fff', borderRadius: '8px', padding: '20px',
    marginBottom: '24px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
  },
  infoGrid: { display: 'flex', gap: '32px', flexWrap: 'wrap' },
  infoLabel: { fontSize: '0.78rem', color: '#7f8c8d', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' },
  infoValue: { fontSize: '0.95rem', color: '#2c3e50', marginTop: '2px', fontWeight: 500 },
  sectionHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px',
  },
  sectionTitle: { margin: 0, color: '#2c3e50', fontSize: '1.1rem' },
  newBtn: {
    background: '#27ae60', color: '#fff', border: 'none',
    borderRadius: '6px', padding: '7px 16px', cursor: 'pointer', fontWeight: 600,
  },
  table: {
    width: '100%', borderCollapse: 'collapse', background: '#fff',
    borderRadius: '8px', overflow: 'hidden',
  },
  th: {
    padding: '11px 16px', background: '#ecf0f1', textAlign: 'left',
    fontWeight: 700, fontSize: '0.88rem', color: '#2c3e50', borderBottom: '1px solid #dce1e7',
  },
  tr: { borderBottom: '1px solid #ecf0f1' },
  td: { padding: '11px 16px', fontSize: '0.9rem', color: '#34495e', verticalAlign: 'middle' },
  link: { color: '#3498db', textDecoration: 'none', fontWeight: 600 },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px',
  },
  pagination: { marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' },
  pageBtn: { padding: '6px 14px', border: '1px solid #dce1e7', borderRadius: '6px', cursor: 'pointer', background: '#fff' },
  pageLabel: { color: '#7f8c8d', fontSize: '0.9rem' },
}
