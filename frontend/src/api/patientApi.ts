// design_doc §4.2 — Patient management endpoints (Clinician / Admin)
import axios from 'axios'
import { getAccessToken } from './authApi'

const BASE = '/api/v1'

export interface Patient {
  id: number
  name: string
  date_of_birth: string
  gender: 'male' | 'female' | 'other'
  contact_email?: string
  // ID of the linked client User account (null if no account linked)
  linked_user: number | null
  created_at: string
}

export interface CreatePatientPayload {
  name: string
  date_of_birth: string
  gender: 'male' | 'female' | 'other'
  contact_email?: string
  linked_user?: number   // client User.id to link this patient to their account
}

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function listPatients(): Promise<Patient[]> {
  const res = await axios.get<Patient[]>(`${BASE}/patients/`, { headers: authHeaders() })
  return res.data
}

export async function createPatient(data: CreatePatientPayload): Promise<Patient> {
  const res = await axios.post<Patient>(`${BASE}/patients/`, data, { headers: authHeaders() })
  return res.data
}

export async function getPatient(id: number): Promise<Patient> {
  const res = await axios.get<Patient>(`${BASE}/patients/${id}/`, { headers: authHeaders() })
  return res.data
}

export async function updatePatient(id: number, data: Partial<CreatePatientPayload>): Promise<Patient> {
  const res = await axios.put<Patient>(`${BASE}/patients/${id}/`, data, { headers: authHeaders() })
  return res.data
}

// Admin only — soft delete
export async function deletePatient(id: number): Promise<void> {
  await axios.delete(`${BASE}/patients/${id}/`, { headers: authHeaders() })
}
