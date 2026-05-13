// design_doc §1 — Three roles: admin / clinician / client
// Routes are guarded by PrivateRoute which checks auth + optional role list.
// Admin is redirected to /admin (user management) instead of the diagnosis list.
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { useAuth } from './context/AuthContext'
import PrivateRoute from './router/PrivateRoute'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import DiagnosisListPage from './pages/DiagnosisListPage'
import DiagnosisSubmitPage from './pages/DiagnosisSubmitPage'
import DiagnosisDetailPage from './pages/DiagnosisDetailPage'
import ReportDownloadPage from './pages/ReportDownloadPage'

// Redirects admin to /admin; everyone else sees the diagnosis list.
function HomeRoute() {
  const { user } = useAuth()
  if (user?.role === 'admin') return <Navigate to="/admin" replace />
  return <DiagnosisListPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Root: admin → /admin, others → diagnosis list */}
          <Route path="/" element={
            <PrivateRoute><HomeRoute /></PrivateRoute>
          } />

          {/* Admin only: user management */}
          <Route path="/admin" element={
            <PrivateRoute roles={['admin']}><AdminPage /></PrivateRoute>
          } />

          {/* Clinician only: submit a new diagnosis */}
          <Route path="/diagnosis/submit" element={
            <PrivateRoute roles={['clinician']}><DiagnosisSubmitPage /></PrivateRoute>
          } />

          {/* All roles: polling detail page */}
          <Route path="/diagnosis/:id" element={
            <PrivateRoute><DiagnosisDetailPage /></PrivateRoute>
          } />

          {/* All roles: PDF download page */}
          <Route path="/diagnosis/:id/report" element={
            <PrivateRoute><ReportDownloadPage /></PrivateRoute>
          } />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
