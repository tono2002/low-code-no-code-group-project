import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import Header from '../components/Header'

function formatPrice(min, max) {
  const fmt = (n) => {
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

export default function Feed() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="page">
      <Header />
      <main className="container">
        {loading && <p className="muted">Loading listings…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && listings.length === 0 && (
          <div className="empty">
            <p>No listings yet.</p>
            <p className="muted">Be the first — hit “Sell” to post something.</p>
          </div>
        )}

        <div className="grid">
          {listings.map((item) => (
            <article className="listing-card" key={item.id}>
              <div className="thumb">
                {item.image_url ? (
                  <img src={item.image_url} alt={item.title} loading="lazy" />
                ) : (
                  <div className="thumb-placeholder">No photo</div>
                )}
              </div>
              <div className="listing-body">
                <h3 className="listing-title">{item.title || 'Untitled'}</h3>
                {item.category && <span className="chip">{item.category}</span>}
                <p className="price">{formatPrice(item.price_min, item.price_max)}</p>
              </div>
            </article>
          ))}
        </div>
      </main>
    </div>
  )
}
