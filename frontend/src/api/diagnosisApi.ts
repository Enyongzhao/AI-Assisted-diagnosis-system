// design_doc §4.3 — Diagnosis task endpoints (core)
import axios from 'axios'
import { getAccessToken } from './authApi'

const BASE = '/api/v1'

// --- Types matching design_doc API shapes ---

export interface StructuredData {
  age: number
  gender: string
  temperature: number
  blood_pressure: string
  heart_rate: number
  symptoms: string[]
  duration_days: number
  existing_conditions: string[]
}

export interface SubmitDiagnosisPayload {
  patient_id: number
  structured_data: StructuredData
  free_text: string
}

export interface SubmitDiagnosisResponse {
  diagnosis_id: string
  status: string
  submitted_at: string
  message: string
  // Soft warning fields (design_doc §4.3 — POSSIBLE_DUPLICATE)
  warning?: string
  warning_message?: string
  previous_diagnosis_id?: string
}

export interface LLMReport {
  summary: string
  differential_diagnosis: string[]
  recommended_investigations: string[]
  risk_factors: string[]
  generated_by: string
  generated_at: string
}

export interface DoctorOpinion {
  text: string
  submitted_by: string
  submitted_at: string
}

export type DiagnosisStatus =
  | 'pending'
  | 'processing'
  | 'awaiting_doctor_input'
  | 'generating_pdf'
  | 'completed'
  | 'failed'

export interface DiagnosisDetail {
  diagnosis_id: string
  status: DiagnosisStatus
  submitted_at: string
  completed_at?: string
  // design_doc §4.3 Phase 4 — duplicate detection warning fields
  has_warning: boolean
  warning_type: string | null   // "POSSIBLE_DUPLICATE" or null
  llm_report: LLMReport | null
  doctor_opinion: DoctorOpinion | null
  pdf_url?: string
}

export interface DiagnosisListItem {
  diagnosis_id: string
  patient_id: number
  patient_name: string
  status: DiagnosisStatus
  submitted_at: string
}

export interface DiagnosisListResponse {
  count: number
  next: string | null
  previous: string | null
  results: DiagnosisListItem[]
}

export interface ReportUrlResponse {
  diagnosis_id: string
  pdf_url: string
  expires_at: string
}

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// POST /api/v1/diagnosis/ — Clinician submits new diagnosis task
export async function submitDiagnosis(payload: SubmitDiagnosisPayload): Promise<SubmitDiagnosisResponse> {
  const res = await axios.post<SubmitDiagnosisResponse>(`${BASE}/diagnosis/`, payload, {
    headers: authHeaders(),
  })
  return res.data
}

// GET /api/v1/diagnosis/{id}/ — Poll status and retrieve LLM report
export async function getDiagnosis(id: string): Promise<DiagnosisDetail> {
  const res = await axios.get<DiagnosisDetail>(`${BASE}/diagnosis/${id}/`, {
    headers: authHeaders(),
  })
  return res.data
}

// GET /api/v1/diagnosis/ — List diagnoses (filtered by role on the backend)
export async function listDiagnoses(params?: {
  status?: string
  patient_id?: number
  page?: number
  page_size?: number
}): Promise<DiagnosisListResponse> {
  const res = await axios.get<DiagnosisListResponse>(`${BASE}/diagnosis/`, {
    headers: authHeaders(),
    params,
  })
  return res.data
}

// PATCH /api/v1/diagnosis/{id}/opinion/ — Clinician submits doctor opinion
export async function submitOpinion(id: string, text: string): Promise<{ diagnosis_id: string; status: string; message: string }> {
  const res = await axios.patch(
    `${BASE}/diagnosis/${id}/opinion/`,
    { text },
    { headers: authHeaders() }
  )
  return res.data
}

// GET /api/v1/diagnosis/{id}/report/ — Get PDF pre-signed URL (15 min TTL)
export async function getReportUrl(id: string): Promise<ReportUrlResponse> {
  const res = await axios.get<ReportUrlResponse>(`${BASE}/diagnosis/${id}/report/`, {
    headers: authHeaders(),
  })
  return res.data
}
