// design_doc §1 — Three roles: admin / clinician / client
// Provides global auth state: user info, login/logout, and current role.
import React, { createContext, useContext, useState, useCallback } from 'react'
import {
  login as apiLogin,
  saveTokens,
  saveUser,
  clearTokens,
  loadUser,
  type AuthUser,
} from '../api/authApi'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  // Returns the logged-in user so callers can redirect based on role immediately.
  login: (username: string, password: string) => Promise<AuthUser>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Restore user from localStorage on page refresh
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const login = useCallback(async (username: string, password: string): Promise<AuthUser> => {
    const data = await apiLogin(username, password)
    saveTokens(data.access, data.refresh)
    saveUser(data.user)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// Throws if called outside AuthProvider — forces correct usage.
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
