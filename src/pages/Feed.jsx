import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'

function formatPrice(min, max) {
  const fmt = n => {
    if (n === null || n === undefined || n === '') return null
    const num = Number(n)
    return Number.isNaN(num) ? null : num.toLocaleString('en-IE')
  }
  const lo = fmt(min)
  const hi = fmt(max)
  if (lo === null && hi === null) return 'Price on request'
  if (lo !== null && hi !== null) return lo === hi ? `€${lo}` : `€${lo}–${hi}`
  return `€${lo ?? hi}`
}

const CATEGORY_COLORS = {
  'Electronics':   '#2563eb',
  'Books & Notes': '#7c3aed',
  'Furniture':     '#0891b2',
  'Calculators':   '#059669',
  'Lab & Supplies':'#d97706',
  'Other':         '#6b7280',
}

export default function Feed() {
  const { user } = useAuth()
  const [listings, setListings] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    let active = true
    ;(async () => {
      const { data, error } = await supabase
        .from('listings')
        .select('*')
        .order('created_at', { ascending: false })
      if (!active) return
      if (error) setError(error.message)
      else setListings(data || [])
      setLoading(false)
    })()
    return () => { active = false }
  }, [])

  // Sold items drop out of the feed. Filtering in JS (not the query) keeps this
  // safe before the `status` column exists — undefined status counts as active.
  const visible = listings.filter(item => item.status !== 'sold')

  // Owner marks their listing sold → it leaves the feed. The optional final price
  // feeds the price-training automation (Zap 1/4). Requires the status/sold_at/
  // sale_price columns; until they exist this surfaces a visible error on click.
  async function markAsSold(item) {
    setError('')
    const input = window.prompt('Mark as sold — final sale price in € (optional):', item.price_max ?? '')
    if (input === null) return // cancelled
    const trimmed = input.trim()
    const sale_price = trimmed === '' ? null : Number(trimmed)
    if (sale_price !== null && Number.isNaN(sale_price)) {
      setError('Please enter a number for the sale price.')
      return
    }
    const { error: updErr } = await supabase
      .from('listings')
      .update({ status: 'sold', sold_at: new Date().toISOString(), sale_price })
      .eq('id', item.id)
    if (updErr) { setError(updErr.message); return }
    setListings(prev => prev.map(l => (l.id === item.id ? { ...l, status: 'sold' } : l)))
  }

  return (
    <div className="app-page">
      <Header />
      <main className="app-container">

        {loading && (
          <div className="feed-loading">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="feed-skeleton" style={{ '--i': i }} />
            ))}
          </div>
        )}

        {error && <p className="error">{error}</p>}

        {!loading && !error && visible.length === 0 && (
          <div className="feed-empty">
            <div className="feed-empty-icon">🛍️</div>
            <h2>Nothing here yet</h2>
            <p>Be the first — hit <strong>+ Sell</strong> to post something.</p>
          </div>
        )}

        {!loading && visible.length > 0 && (
          <div className="feed-grid">
            {visible.map(item => {
              const color = CATEGORY_COLORS[item.category] || '#6b7280'
              return (
                <article className="feed-card" key={item.id} style={{ '--cc': color }}>
                  <div className="feed-card-img">
                    {item.image_url
                      ? <img src={item.image_url} alt={item.title} loading="lazy" />
                      : <div className="feed-card-no-img">No photo</div>
                    }
                    {item.category && (
                      <span className="feed-card-chip">{item.category}</span>
                    )}
                  </div>
                  <div className="feed-card-body">
                    <h3 className="feed-card-title">{item.title || 'Untitled'}</h3>
                    {item.description && (
                      <p className="feed-card-desc">{item.description}</p>
                    )}
                    <div className="feed-card-footer">
                      <span className="feed-card-price">{formatPrice(item.price_min, item.price_max)}</span>
                      {user && item.user_id === user.id
                        ? <button
                            type="button"
                            className="feed-card-sold-btn"
                            onClick={() => markAsSold(item)}
                            style={{
                              border: '1px solid var(--cc, #2563eb)',
                              color: 'var(--cc, #2563eb)',
                              background: 'transparent',
                              borderRadius: 8,
                              padding: '5px 10px',
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Mark as sold
                          </button>
                        : <span className="feed-card-view">View →</span>
                      }
                    </div>
                  </div>
                  <div className="feed-card-glow" />
                </article>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
