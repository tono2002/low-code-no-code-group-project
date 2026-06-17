import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Auth from './pages/Auth'
import Feed from './pages/Feed'
import Sell from './pages/Sell'
import Landing from './pages/Landing'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="centered">
        <p>Loading…</p>
      </div>
    )
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Auth />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Feed />} />
      <Route path="/sell" element={<Sell />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
