import { useNavigate } from 'react-router-dom'
import { supabase } from '../supabaseClient'
import { useAuth } from '../context/AuthContext'

export default function Header({ showSell = true }) {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <header className="header">
      <button className="brand-link" type="button" onClick={() => navigate('/')}>
        🎓 Student Marketplace
      </button>
      <div className="header-actions">
        {showSell && (
          <button className="btn primary" type="button" onClick={() => navigate('/sell')}>
            + Sell
          </button>
        )}
        {user && <span className="muted email">{user.email}</span>}
        <button className="btn ghost" type="button" onClick={() => supabase.auth.signOut()}>
          Log out
        </button>
      </div>
    </header>
  )
}
