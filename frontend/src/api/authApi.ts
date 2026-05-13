// design_doc §4.1 — POST /api/v1/auth/login/ and /api/v1/auth/refresh/
import axios from 'axios'

const BASE = '/api/v1'

export interface AuthUser {
  id: number
  username: string
  role: 'admin' | 'clinician' | 'client'
}

export interface LoginResponse {
  access: string
  refresh: string
  user: AuthUser
}

// --- Token helpers (persisted in localStorage) ---

export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export function clearTokens(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('auth_user')
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

export function saveUser(user: AuthUser): void {
  localStorage.setItem('auth_user', JSON.stringify(user))
}

export function loadUser(): AuthUser | null {
  const raw = localStorage.getItem('auth_user')
  if (!raw) return null
  try { return JSON.parse(raw) as AuthUser } catch { return null }
}

// --- API calls ---

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await axios.post<LoginResponse>(`${BASE}/auth/login/`, { username, password })
  return res.data
}

// Refreshes the access token using the stored refresh token.
export async function refreshAccessToken(): Promise<string> {
  const refresh = getRefreshToken()
  if (!refresh) throw new Error('No refresh token available')
  const res = await axios.post<{ access: string }>(`${BASE}/auth/refresh/`, { refresh })
  return res.data.access
}
