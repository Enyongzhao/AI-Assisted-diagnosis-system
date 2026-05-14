// design_doc §1 — Three roles: admin / clinician / client
// Admin  → /admin        (user management)
// Clinician → /          (patient list) → /patients/:id → /patients/:id/diagnosis/submit
// Client → /             (own diagnosis reports)
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import PrivateRoute from './router/PrivateRoute'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import PatientListPage from './pages/PatientListPage'
import PatientDetailPage from './pages/PatientDetailPage'
import DiagnosisListPage from './pages/DiagnosisListPage'
import DiagnosisSubmitPage from './pages/DiagnosisSubmitPage'
import DiagnosisDetailPage from './pages/DiagnosisDetailPage'
import ReportDownloadPage from './pages/ReportDownloadPage'

// Role-based home: admin → /admin, clinician → patient list, client → diagnosis list
function HomeRoute() {
  const { user } = useAuth()
  if (user?.role === 'admin') return <Navigate to="/admin" replace />
  if (user?.role === 'clinician') return <PatientListPage />
  return <DiagnosisListPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Home — role-dependent */}
          <Route path="/" element={<PrivateRoute><HomeRoute /></PrivateRoute>} />

          {/* Admin: user management */}
          <Route path="/admin" element={<PrivateRoute roles={['admin']}><AdminPage /></PrivateRoute>} />

          {/* Clinician: per-patient detail + new diagnosis */}
          <Route path="/patients/:patientId" element={<PrivateRoute roles={['clinician']}><PatientDetailPage /></PrivateRoute>} />
          <Route path="/patients/:patientId/diagnosis/submit" element={<PrivateRoute roles={['clinician']}><DiagnosisSubmitPage /></PrivateRoute>} />

          {/* All roles: diagnosis detail (polling) */}
          <Route path="/diagnosis/:id" element={<PrivateRoute><DiagnosisDetailPage /></PrivateRoute>} />

          {/* All roles: PDF download */}
          <Route path="/diagnosis/:id/report" element={<PrivateRoute><ReportDownloadPage /></PrivateRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
