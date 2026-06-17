import { useNavigate } from 'react-router-dom'
import { supabase } from '../supabaseClient'
import { useAuth } from '../context/AuthContext'

export default function Header({ showSell = true }) {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <header className="app-header">
      <button className="app-brand" type="button" onClick={() => navigate('/')}>
        🎓 <span>Student Marketplace</span>
      </button>
      <div className="app-header-right">
        {showSell && (
          <button className="app-header-sell" type="button" onClick={() => navigate('/sell')}>
            + Sell
          </button>
        )}
        {user && <span className="app-header-email">{user.email}</span>}
        <button
          className="app-header-logout"
          type="button"
          onClick={() => supabase.auth.signOut()}
        >
          Log out
        </button>
      </div>
    </header>
  )
}
