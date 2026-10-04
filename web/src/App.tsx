import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AttemptsPage from './pages/AttemptsPage'
import AttemptDetailPage from './pages/AttemptDetailPage'
import StudentsPage from './pages/StudentsPage'
import VariantsPage from './pages/VariantsPage'
import VariantDetailPage from './pages/VariantDetailPage'
import ConversionTablesPage from './pages/ConversionTablesPage'
import StatsPage from './pages/StatsPage'
import SettingsPage from './pages/SettingsPage'

function Protected() {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return <AppLayout />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Protected />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/attempts" element={<AttemptsPage />} />
            <Route path="/attempts/:id" element={<AttemptDetailPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/variants" element={<VariantsPage />} />
            <Route path="/variants/:id" element={<VariantDetailPage />} />
            <Route path="/conversion-tables" element={<ConversionTablesPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}