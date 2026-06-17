import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
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

        {!loading && !error && listings.length === 0 && (
          <div className="feed-empty">
            <div className="feed-empty-icon">🛍️</div>
            <h2>Nothing here yet</h2>
            <p>Be the first — hit <strong>+ Sell</strong> to post something.</p>
          </div>
        )}

        {!loading && listings.length > 0 && (
          <div className="feed-grid">
            {listings.map(item => {
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
                      <span className="feed-card-view">View →</span>
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
