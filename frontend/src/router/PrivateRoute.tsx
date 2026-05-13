// design_doc §1 — Route guard: checks authentication + optional role list.
// Unauthenticated users are redirected to /login.
// Authenticated users without the required role see a 403-style message.
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface Props {
  children: React.ReactNode
  // If provided, the current user's role must be in this list.
  roles?: string[]
}

export default function PrivateRoute({ children, roles }: Props) {
  const { user, isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (roles && user && !roles.includes(user.role)) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>Access Denied</h2>
        <p>You do not have permission to view this page.</p>
      </div>
    )
  }

  return <>{children}</>
}
