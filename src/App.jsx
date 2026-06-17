import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Auth from './pages/Auth'
import Feed from './pages/Feed'
import Sell from './pages/Sell'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="centered">
        <p>Loading…</p>
      </div>
    )
  }

  // Logged-out users only ever see the auth page.
  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Auth />} />
      </Routes>
    )
  }

  // Logged-in users get the app.
  return (
    <Routes>
      <Route path="/" element={<Feed />} />
      <Route path="/sell" element={<Sell />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
