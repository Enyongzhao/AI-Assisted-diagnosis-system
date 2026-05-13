// design_doc §4.3 — POST /api/v1/diagnosis/ (Clinician only)
// Clinician first selects an existing patient (GET /api/v1/patients/) or creates
// a new one, then fills structured + free-text clinical data and submits.
// This ensures diagnoses for linked patients (e.g. patient01 ↔ John Smith) are
// visible to the corresponding Client account.
import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitDiagnosis } from '../api/diagnosisApi'
import { listPatients, createPatient, type Patient } from '../api/patientApi'
import WarningBanner from '../components/WarningBanner'

type PatientMode = 'select' | 'create'

export default function DiagnosisSubmitPage() {
  const navigate = useNavigate()

  // ── Patient section ──────────────────────────────────────────────────────
  const [patientMode, setPatientMode] = useState<PatientMode>('select')
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<number | ''>('')
  const [patientsLoading, setPatientsLoading] = useState(true)

  // New-patient fields (only used when patientMode === 'create')
  const [patientName, setPatientName] = useState('')
  const [dob, setDob] = useState('')
  const [patientGender, setPatientGender] = useState<'male' | 'female' | 'other'>('male')
  const [contactEmail, setContactEmail] = useState('')

  // ── Clinical data ────────────────────────────────────────────────────────
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

  // Load existing patients for the dropdown
  useEffect(() => {
    listPatients()
      .then(data => setPatients(data))
      .catch(() => { /* non-fatal — clinician can still create new */ })
      .finally(() => setPatientsLoading(false))
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setWarning(null)
    setLoading(true)

    try {
      let patientId: number

      if (patientMode === 'select') {
        if (!selectedPatientId) {
          setError('Please select a patient.')
          setLoading(false)
          return
        }
        patientId = selectedPatientId as number
      } else {
        // Create new patient first
        const patient = await createPatient({
          name: patientName,
          date_of_birth: dob,
          gender: patientGender,
          contact_email: contactEmail || undefined,
        })
        patientId = patient.id
      }

      const symptoms = symptomsRaw.split(',').map(s => s.trim()).filter(Boolean)
      const conditions = conditionsRaw.split(',').map(s => s.trim()).filter(Boolean)

      const res = await submitDiagnosis({
        patient_id: patientId,
        structured_data: {
          age: parseInt(age),
          gender: patientGender,
          temperature: parseFloat(temperature),
          blood_pressure: bloodPressure,
          heart_rate: parseInt(heartRate),
          symptoms,
          duration_days: parseInt(durationDays),
          existing_conditions: conditions,
        },
        free_text: freeText,
      })

      // design_doc §4.3 — POSSIBLE_DUPLICATE soft warning
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

  return (
    <div style={styles.page}>
      <header style={styles.nav}>
        <span style={styles.navTitle}>AI Diagnosis System</span>
        <button style={styles.backBtn} onClick={() => navigate('/')}>← Back to List</button>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>Submit New Diagnosis</h2>

        {warning && <WarningBanner message={warnMsg} previousId={prevId} />}
        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>

          {/* ── Patient Section ── */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Patient</h3>

            {/* Toggle */}
            <div style={styles.toggleRow}>
              <button
                type="button"
                style={patientMode === 'select' ? styles.toggleActive : styles.toggle}
                onClick={() => setPatientMode('select')}
              >
                Select existing patient
              </button>
              <button
                type="button"
                style={patientMode === 'create' ? styles.toggleActive : styles.toggle}
                onClick={() => setPatientMode('create')}
              >
                Create new patient
              </button>
            </div>

            {patientMode === 'select' ? (
              <div style={{ marginTop: '12px' }}>
                <label style={styles.label}>Patient</label>
                {patientsLoading ? (
                  <p style={{ fontSize: '0.9rem', color: '#7f8c8d' }}>Loading patients…</p>
                ) : patients.length === 0 ? (
                  <p style={{ fontSize: '0.9rem', color: '#e74c3c' }}>
                    No patients found. Switch to "Create new patient".
                  </p>
                ) : (
                  <select
                    style={styles.input}
                    required
                    value={selectedPatientId}
                    onChange={e => setSelectedPatientId(Number(e.target.value))}
                  >
                    <option value="">— Select a patient —</option>
                    {patients.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name} (DOB: {p.date_of_birth}, {p.gender}){p.linked_user ? ' ✓ has account' : ''}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            ) : (
              <>
                <div style={{ ...styles.row, marginTop: '12px' }}>
                  <Field label="Full Name">
                    <input style={styles.input} required value={patientName} onChange={e => setPatientName(e.target.value)} />
                  </Field>
                  <Field label="Date of Birth">
                    <input style={styles.input} type="date" required value={dob} onChange={e => setDob(e.target.value)} />
                  </Field>
                </div>
                <div style={styles.row}>
                  <Field label="Gender">
                    <select style={styles.input} value={patientGender} onChange={e => setPatientGender(e.target.value as typeof patientGender)}>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </Field>
                  <Field label="Contact Email (optional)">
                    <input style={styles.input} type="email" value={contactEmail} onChange={e => setContactEmail(e.target.value)} />
                  </Field>
                </div>
              </>
            )}
          </section>

          {/* ── Clinical Data ── */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Clinical Data</h3>
            <div style={styles.row}>
              <Field label="Age">
                <input style={styles.input} type="number" required min={0} max={150} value={age} onChange={e => setAge(e.target.value)} />
              </Field>
              <Field label="Temperature (°C)">
                <input style={styles.input} type="number" step="0.1" required value={temperature} onChange={e => setTemperature(e.target.value)} />
              </Field>
            </div>
            <div style={styles.row}>
              <Field label="Blood Pressure (e.g. 130/85)">
                <input style={styles.input} required value={bloodPressure} onChange={e => setBloodPressure(e.target.value)} />
              </Field>
              <Field label="Heart Rate (bpm)">
                <input style={styles.input} type="number" required value={heartRate} onChange={e => setHeartRate(e.target.value)} />
              </Field>
            </div>
            <div style={styles.row}>
              <Field label="Symptoms (comma-separated)">
                <input style={styles.input} required placeholder="cough, fatigue, fever" value={symptomsRaw} onChange={e => setSymptomsRaw(e.target.value)} />
              </Field>
              <Field label="Duration (days)">
                <input style={styles.input} type="number" required min={0} value={durationDays} onChange={e => setDurationDays(e.target.value)} />
              </Field>
            </div>
            <Field label="Existing Conditions (comma-separated, or leave blank)">
              <input style={styles.input} placeholder="hypertension, diabetes" value={conditionsRaw} onChange={e => setConditionsRaw(e.target.value)} />
            </Field>
          </section>

          {/* ── Free Text ── */}
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

          <button style={styles.submitBtn} type="submit" disabled={loading}>
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
  main: { maxWidth: '800px', margin: '0 auto', padding: '24px' },
  heading: { marginTop: 0, color: '#2c3e50' },
  form: { display: 'flex', flexDirection: 'column', gap: '0' },
  section: {
    background: '#fff', borderRadius: '8px', padding: '20px',
    marginBottom: '16px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
  },
  sectionTitle: { margin: '0 0 14px', fontSize: '1rem', color: '#2c3e50' },
  row: { display: 'flex', gap: '16px', marginBottom: '12px' },
  label: { fontWeight: 600, fontSize: '0.88rem', color: '#34495e', marginBottom: '4px', display: 'block' },
  input: {
    padding: '8px 12px', border: '1px solid #dce1e7', borderRadius: '6px',
    fontSize: '0.93rem', width: '100%', boxSizing: 'border-box',
  },
  toggleRow: { display: 'flex', gap: '8px' },
  toggle: {
    padding: '6px 14px', border: '1px solid #dce1e7', borderRadius: '20px',
    background: '#fff', cursor: 'pointer', fontSize: '0.88rem', color: '#7f8c8d',
  },
  toggleActive: {
    padding: '6px 14px', border: '1px solid #3498db', borderRadius: '20px',
    background: '#eaf4fb', cursor: 'pointer', fontSize: '0.88rem',
    color: '#1a6fa1', fontWeight: 600,
  },
  submitBtn: {
    padding: '12px', background: '#27ae60', color: '#fff', border: 'none',
    borderRadius: '8px', fontSize: '1rem', fontWeight: 700, cursor: 'pointer',
    marginTop: '8px',
  },
  errorBox: {
    background: '#fdecea', color: '#c0392b', border: '1px solid #f5c6cb',
    borderRadius: '6px', padding: '10px 14px', marginBottom: '16px',
  },
}
