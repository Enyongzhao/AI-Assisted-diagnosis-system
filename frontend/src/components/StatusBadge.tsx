// design_doc §4.3 — diagnosis status values: pending/processing/awaiting_doctor_input/
//                    generating_pdf/completed/failed
import type { DiagnosisStatus } from '../api/diagnosisApi'

interface Props {
  status: DiagnosisStatus
}

const STATUS_CONFIG: Record<DiagnosisStatus, { label: string; color: string }> = {
  pending:               { label: 'Pending',               color: '#f0ad4e' },
  processing:            { label: 'Processing',            color: '#5bc0de' },
  awaiting_doctor_input: { label: 'Awaiting Doctor Input', color: '#428bca' },
  generating_pdf:        { label: 'Generating PDF',        color: '#9b59b6' },
  completed:             { label: 'Completed',             color: '#5cb85c' },
  failed:                { label: 'Failed',                color: '#d9534f' },
}

export default function StatusBadge({ status }: Props) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: '#aaa' }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: '12px',
        backgroundColor: cfg.color,
        color: '#fff',
        fontSize: '0.82rem',
        fontWeight: 600,
        letterSpacing: '0.02em',
      }}
    >
      {cfg.label}
    </span>
  )
}
