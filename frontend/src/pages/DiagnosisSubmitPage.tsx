// design_doc §4.3 — POST /api/v1/diagnosis/ (Clinician only)
// Patient is already known from the URL param — no patient selection needed.
import { useState, useEffect, type FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { submitDiagnosis } from '../api/diagnosisApi'
import { getPatient, type Patient } from '../api/patientApi'
import WarningBanner from '../components/WarningBanner'

export default function DiagnosisSubmitPage() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()

  const [patient, setPatient] = useState<Patient | null>(null)
  const [patientError, setPatientError] = useState<string | null>(null)

  // Clinical data fields
  const [age, setAge] = useState('')
  const [temperature, setTemperature] = useState('')
  const [bloodPressure, setBloodPressure] = useState('')
  const [heartRate, setHeartRate] = useState('')
  const [symptomsRaw, setSymptomsRaw] = useState('')
  const [durationDays, setDurationDays] = useState('')
  const [conditionsRaw, setConditionsRaw] = useState('')
  const [freeText, setFreeText] = useState('')

  const [warning, setWarning] = useState<string | null>(null)
  const [warnMsg, setWarnMsg] = useState('')
  const [prevId, setPrevId] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Load patient info to display name and pre-fill gender
  useEffect(() => {
    if (!patientId) return
    getPatient(parseInt(patientId))
      .then(p => setPatient(p))
      .catch(() => setPatientError('Patient not found.'))
  }, [patientId])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!patientId || !patient) return
    setError(null)
    setWarning(null)
    setLoading(true)

    try {
      const symptoms = symptomsRaw.split(',').map(s => s.trim()).filter(Boolean)
      const conditions = conditionsRaw.split(',').map(s => s.trim()).filter(Boolean)

      const res = await submitDiagnosis({
        patient_id: parseInt(patientId),
        structured_data: {
          age: parseInt(age),
          gender: patient.gender,
          temperature: parseFloat(temperature),
          blood_pressure: bloodPressure,
          heart_rate: parseInt(heartRate),
          symptoms,
          duration_days: parseInt(durationDays),
          existing_conditions: conditions,
        },
        free_text: freeText,
      })

      if (res.warning === 'POSSIBLE_DUPLICATE') {
        setWarning(res.warning)
        setWarnMsg(res.warning_message ?? '')
        setPrevId(res.previous_diagnosis_id)
        setTimeout(() => navigate(`/diagnosis/${res.diagnosis_id}`), 2500)
      } else {
        navigate(`/diagnosis/${res.diagnosis_id}`)
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string; error?: string } } })
          ?.response?.data?.message ??
        (err as { response?: { data?: { error?: string } } })
          ?.response?.data?.error ??
        'Failed to submit diagnosis.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const backPath = patientId ? `/patients/${patientId}` : '/'

  return (
    <div style={styles.page}>
      <header style={styles.nav}>
        <span style={styles.navTitle}>AI Diagnosis System</span>
        <button style={styles.backBtn} onClick={() => navigate(backPath)}>← Back</button>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>New Diagnosis</h2>

        {/* Patient context banner */}
        {patientError && <div style={styles.errorBox}>{patientError}</div>}
        {patient && (
          <div style={styles.patientBanner}>
            <span style={styles.patientLabel}>Patient</span>
            <span style={styles.patientName}>{patient.name}</span>
            <span style={styles.patientMeta}>
              DOB: {patient.date_of_birth} · {patient.gender}
            </span>
          </div>
        )}

        {warning && <WarningBanner message={warnMsg} previousId={prevId} />}
        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>

          {/* Clinical Data */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Clinical Data</h3>
            <div style={styles.row}>
              <Field label="Age">
                <input style={styles.input} type="number" required min={0} max={150}
                  value={age} onChange={e => setAge(e.target.value)} />
              </Field>
              <Field label="Temperature (°C)">
                <input style={styles.input} type="number" step="0.1" required
                  value={temperature} onChange={e => setTemperature(e.target.value)} />
              </Field>
            </div>
            <div style={styles.row}>
              <Field label="Blood Pressure (e.g. 130/85)">
                <input style={styles.input} required value={bloodPressure}
                  onChange={e => setBloodPressure(e.target.value)} />
              </Field>
              <Field label="Heart Rate (bpm)">
                <input style={styles.input} type="number" required value={heartRate}
                  onChange={e => setHeartRate(e.target.value)} />
              </Field>
            </div>
            <div style={styles.row}>
              <Field label="Symptoms (comma-separated)">
                <input style={styles.input} required placeholder="cough, fatigue, fever"
                  value={symptomsRaw} onChange={e => setSymptomsRaw(e.target.value)} />
              </Field>
              <Field label="Duration (days)">
                <input style={styles.input} type="number" required min={0}
                  value={durationDays} onChange={e => setDurationDays(e.target.value)} />
              </Field>
            </div>
            <Field label="Existing Conditions (comma-separated, or leave blank)">
              <input style={styles.input} placeholder="hypertension, diabetes"
                value={conditionsRaw} onChange={e => setConditionsRaw(e.target.value)} />
            </Field>
          </section>

          {/* Clinical Notes */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Clinical Notes</h3>
            <textarea
              style={{ ...styles.input, minHeight: '120px', resize: 'vertical' }}
              required
              placeholder="Describe the patient's presenting complaint, history, and any additional observations…"
              value={freeText}
              onChange={e => setFreeText(e.target.value)}
            />
          </section>

          <button style={styles.submitBtn} type="submit" disabled={loading || !patient}>
            {loading ? 'Submitting…' : 'Submit Diagnosis'}
          </button>
        </form>
      </main>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
      <label style={{ fontWeight: 600, fontSize: '0.88rem', color: '#34495e' }}>{label}</label>
      {children}
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
  main: { maxWidth: '760px', margin: '0 auto', padding: '24px' },
  heading: { marginTop: 0, color: '#2c3e50' },
  patientBanner: {
    background: '#eaf4fb', border: '1px solid #85c1e9', borderRadius: '8px',
    padding: '12px 16px', marginBottom: '20px',
    display: 'flex', alignItems: 'center', gap: '12px',
  },
  patientLabel: { fontSize: '0.78rem', fontWeight: 700, color: '#1a6fa1', textTransform: 'uppercase', letterSpacing: '0.05em' },
  patientName: { fontSize: '1rem', fontWeight: 700, color: '#1a5276' },
  patientMeta: { fontSize: '0.88rem', color: '#5d8eaa' },
  form: { display: 'flex', flexDirection: 'column', gap: '0' },
  section: {
    background: '#fff', borderRadius: '8px', padding: '20px',
    marginBottom: '16px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
  },
  sectionTitle: { margin: '0 0 14px', fontSize: '1rem', color: '#2c3e50' },
  row: { display: 'flex', gap: '16px', marginBottom: '12px' },
  input: {
    padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px',
    fontSize: '0.93rem', width: '100%', boxSizing: 'border-box',
  },
  submitBtn: {
    padding: '12px', background: '#27ae60', color: '#fff', border: 'none',
    borderRadius: '8px', fontSize: '1rem', fontWeight: 700, cursor: 'pointer',
  },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px', marginBottom: '16px',
  },
}
