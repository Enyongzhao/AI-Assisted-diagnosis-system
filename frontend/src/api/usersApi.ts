// design_doc §4.4 — Admin-only user management endpoints
import axios from 'axios'
import { getAccessToken } from './authApi'

const BASE = '/api/v1'

export interface ManagedUser {
  id: number
  username: string
  email: string
  role: 'admin' | 'clinician' | 'client'
  is_active: boolean
  date_joined: string
}

export interface CreateUserPayload {
  username: string
  email: string
  password: string
  role: 'clinician' | 'client'
}

export interface UpdateUserPayload {
  username?: string
  email?: string
  password?: string
  role?: 'clinician' | 'client'
}

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function listUsers(): Promise<ManagedUser[]> {
  const res = await axios.get<ManagedUser[]>(`${BASE}/users/`, { headers: authHeaders() })
  return res.data
}

export async function createUser(data: CreateUserPayload): Promise<ManagedUser> {
  const res = await axios.post<ManagedUser>(`${BASE}/users/`, data, { headers: authHeaders() })
  return res.data
}

export async function updateUser(id: number, data: UpdateUserPayload): Promise<ManagedUser> {
  const res = await axios.put<ManagedUser>(`${BASE}/users/${id}/`, data, { headers: authHeaders() })
  return res.data
}

// Soft-delete: sets is_active=False on the backend
export async function deleteUser(id: number): Promise<void> {
  await axios.delete(`${BASE}/users/${id}/`, { headers: authHeaders() })
}
