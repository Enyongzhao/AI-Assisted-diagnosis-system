// design_doc §4.3 — GET /api/v1/diagnosis/{id}/report/
// Fetches the pre-signed PDF URL (15 min TTL) and triggers download.
// This page is the entry point for Client role and also reachable from DiagnosisDetailPage.
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getReportUrl } from '../api/diagnosisApi'

export default function ReportDownloadPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getReportUrl(id)
      .then(data => {
        setPdfUrl(data.pdf_url)
        setExpiresAt(data.expires_at)
        setLoading(false)
        // Auto-open the PDF in a new tab (works for both S3 pre-signed and local /media/ URLs)
        window.open(data.pdf_url, '_blank')
      })
      .catch(err => {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 403) {
          setError('You do not have permission to access this report.')
        } else {
          setError('Failed to retrieve the report URL. The report may not be ready yet.')
        }
        setLoading(false)
      })
  }, [id])

  return (
    <div style={styles.page}>
      <header style={styles.nav}>
        <span style={styles.navTitle}>AI Diagnosis System</span>
        <button style={styles.backBtn} onClick={() => navigate('/')}>← Back to List</button>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>Download Report</h2>

        {loading && <p>Fetching report URL…</p>}

        {error && <div style={styles.errorBox}>{error}</div>}

        {pdfUrl && (
          <div style={styles.card}>
            <p style={{ marginTop: 0 }}>
              ✅ Your PDF report has been opened in a new tab.
            </p>
            {expiresAt && (
              <p style={styles.meta}>
                Link expires at: {new Date(expiresAt).toLocaleString()}
              </p>
            )}
            <a href={pdfUrl} target="_blank" rel="noreferrer" style={styles.downloadLink}>
              📄 Click here if it did not open automatically
            </a>
          </div>
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
  backBtn: {
    background: 'transparent', color: '#bdc3c7', border: '1px solid #7f8c8d',
    borderRadius: '6px', padding: '5px 12px', cursor: 'pointer',
  },
  main: { maxWidth: '600px', margin: '0 auto', padding: '24px' },
  heading: { marginTop: 0, color: '#2c3e50' },
  card: {
    background: '#fff', borderRadius: '8px', padding: '24px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
  },
  meta: { fontSize: '0.88rem', color: '#7f8c8d' },
  downloadLink: {
    display: 'inline-block', marginTop: '12px',
    color: '#3498db', fontWeight: 600, fontSize: '1rem',
  },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '12px 16px',
  },
}
