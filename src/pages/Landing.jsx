import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const HERO_CARDS = [
  {
    title: 'MacBook Pro 13"',
    category: 'Electronics',
    price: '€850–€950',
    img: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=480&auto=format&fit=crop&q=80',
    ai: true,
  },
  {
    title: 'Organic Chemistry, 9th Ed.',
    category: 'Books & Notes',
    price: '€25–€35',
    img: 'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=480&auto=format&fit=crop&q=80',
    ai: false,
  },
  {
    title: 'Sony WH-1000XM4',
    category: 'Electronics',
    price: '€120–€150',
    img: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=480&auto=format&fit=crop&q=80',
    ai: true,
  },
]

const SHOWCASE = [
  { img: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&auto=format&fit=crop&q=75', label: 'MacBook Pro' },
  { img: 'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400&auto=format&fit=crop&q=75', label: 'Textbooks' },
  { img: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&auto=format&fit=crop&q=75', label: 'Headphones' },
  { img: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&auto=format&fit=crop&q=75', label: 'Bicycle' },
  { img: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&auto=format&fit=crop&q=75', label: 'Coffee Machine' },
  { img: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&auto=format&fit=crop&q=75', label: 'Furniture' },
  { img: 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&auto=format&fit=crop&q=75', label: 'Desk Setup' },
  { img: 'https://images.unsplash.com/photo-1484788984921-03950022c9ef?w=400&auto=format&fit=crop&q=75', label: 'Laptop' },
]

const FEATURES = [
  {
    icon: '✨',
    title: 'AI-powered listings',
    body: 'Snap a photo. Gemini AI writes your title, description, category, and suggested price — in seconds.',
    color: '#6366f1',
  },
  {
    icon: '🎓',
    title: 'Student-only community',
    body: 'A trusted campus marketplace. Buy from and sell to people you actually know.',
    color: '#0ea5e9',
  },
  {
    icon: '⚡',
    title: 'Live in 30 seconds',
    body: 'No approval queues. Upload, generate, publish. Your listing is live instantly.',
    color: '#10b981',
  },
]

const STEPS = [
  { n: '01', title: 'Sign up free', desc: 'Create your account with your student email in seconds. No credit card.' },
  { n: '02', title: 'Snap & let AI list', desc: 'Upload a photo of your item. AI writes the full listing for you.' },
  { n: '03', title: 'Sell on campus', desc: 'Connect with buyers near you. Keep all the money — zero fees.' },
]

// ─── Particle canvas ───────────────────────────────────────────────────────────
function Particles() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const count = Math.min(70, Math.floor(canvas.width / 16))
    const pts = Array.from({ length: count }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.6 + 0.4,
    }))

    let raf
    const tick = () => {
      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)

      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x
          const dy = pts[i].y - pts[j].y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 140) {
            ctx.beginPath()
            ctx.strokeStyle = `rgba(120,160,255,${0.2 * (1 - d / 140)})`
            ctx.lineWidth = 0.7
            ctx.moveTo(pts[i].x, pts[i].y)
            ctx.lineTo(pts[j].x, pts[j].y)
            ctx.stroke()
          }
        }
      }

      pts.forEach(p => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(120,160,255,0.6)'
        ctx.fill()
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > w) p.vx *= -1
        if (p.y < 0 || p.y > h) p.vy *= -1
      })

      raf = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="lp-particles" />
}

// ─── 3D tilt card ─────────────────────────────────────────────────────────────
function TiltCard({ children, className = '', style = {} }) {
  const ref = useRef(null)

  const onMove = e => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const x = e.clientX - r.left
    const y = e.clientY - r.top
    const rx = ((y - r.height / 2) / (r.height / 2)) * 14
    const ry = (-( x - r.width / 2) / (r.width / 2)) * 14
    el.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) scale3d(1.04,1.04,1.04)`
    el.style.transition = 'transform 0.05s ease'
  }

  const onLeave = () => {
    const el = ref.current
    if (!el) return
    el.style.transform = ''
    el.style.transition = 'transform 0.5s ease'
  }

  return (
    <div ref={ref} className={className} style={style} onMouseMove={onMove} onMouseLeave={onLeave}>
      {children}
    </div>
  )
}

// ─── Main component ────────────────────────────────────────────────────────────
export default function Landing() {
  const navigate = useNavigate()
  const glowRef = useRef(null)

  // Cursor glow
  useEffect(() => {
    const el = glowRef.current
    if (!el) return
    let fx = 0, fy = 0
    let tx = 0, ty = 0
    let raf

    const onMove = e => { tx = e.clientX; ty = e.clientY }
    window.addEventListener('mousemove', onMove)

    const animate = () => {
      fx += (tx - fx) * 0.1
      fy += (ty - fy) * 0.1
      el.style.left = fx + 'px'
      el.style.top = fy + 'px'
      raf = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  // Scroll reveal
  useEffect(() => {
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('lp-revealed')
          obs.unobserve(e.target)
        }
      }),
      { threshold: 0.1 }
    )
    document.querySelectorAll('.lp-reveal').forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  return (
    <div className="lp-root">
      {/* Cursor spotlight */}
      <div ref={glowRef} className="lp-cursor-glow" aria-hidden="true" />

      {/* ── Nav ── */}
      <nav className="lp-nav">
        <span className="lp-nav-brand">🎓 Student Marketplace</span>
        <div className="lp-nav-actions">
          <button className="lp-nav-login" onClick={() => navigate('/login')}>Log in</button>
          <button className="lp-nav-signup" onClick={() => navigate('/login?tab=signup')}>Sign up free</button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <Particles />

        {/* Ambient blobs */}
        <div className="lp-blob lp-blob-1" aria-hidden="true" />
        <div className="lp-blob lp-blob-2" aria-hidden="true" />

        <div className="lp-hero-inner">
          <div className="lp-hero-left">
            <div className="lp-hero-badge">✦ Free for students · No listing fees</div>
            <h1 className="lp-hero-title">
              The campus<br />
              marketplace<br />
              <span className="lp-gradient-text">built for you.</span>
            </h1>
            <p className="lp-hero-sub">
              Buy and sell textbooks, electronics, furniture, and more.
              Our AI writes your listing from a single photo.
            </p>
            <div className="lp-hero-ctas">
              <button className="lp-btn-primary" onClick={() => navigate('/login?tab=signup')}>
                Get started free
                <span className="lp-btn-arrow">→</span>
              </button>
              <button className="lp-btn-ghost" onClick={() => navigate('/login')}>
                Browse listings
              </button>
            </div>
            <p className="lp-hero-note">No credit card required</p>
          </div>

          <div className="lp-hero-cards">
            {HERO_CARDS.map((card, i) => (
              <TiltCard key={card.title} className={`lp-hcard lp-hcard-${i + 1}`}>
                <div className="lp-hcard-img">
                  <img src={card.img} alt={card.title} loading="lazy" />
                  {card.ai && <span className="lp-hcard-ai">✨ AI</span>}
                </div>
                <div className="lp-hcard-body">
                  <span className="lp-hcard-chip">{card.category}</span>
                  <p className="lp-hcard-title">{card.title}</p>
                  <p className="lp-hcard-price">{card.price}</p>
                </div>
              </TiltCard>
            ))}
          </div>
        </div>

        <div className="lp-scroll-cue" aria-hidden="true">
          <div className="lp-scroll-mouse"><div className="lp-scroll-wheel" /></div>
          <span>Scroll</span>
        </div>
      </section>

      {/* ── Infinite showcase strip ── */}
      <div className="lp-showcase">
        <div className="lp-showcase-track">
          {[...SHOWCASE, ...SHOWCASE].map((item, i) => (
            <div className="lp-showcase-item" key={i}>
              <img src={item.img} alt={item.label} loading="lazy" />
              <span className="lp-showcase-label">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <section className="lp-features">
        <div className="lp-section-header lp-reveal">
          <p className="lp-eyebrow">Why students choose us</p>
          <h2 className="lp-section-title">Everything you need, nothing you don't</h2>
        </div>
        <div className="lp-features-grid">
          {FEATURES.map((f, i) => (
            <TiltCard
              key={f.title}
              className="lp-fcard lp-reveal"
              style={{ '--fc': f.color, '--fi': i }}
            >
              <div className="lp-fcard-icon">{f.icon}</div>
              <h3 className="lp-fcard-title">{f.title}</h3>
              <p className="lp-fcard-body">{f.body}</p>
              <div className="lp-fcard-glow" />
            </TiltCard>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="lp-how">
        <div className="lp-section-header lp-reveal">
          <p className="lp-eyebrow">Simple by design</p>
          <h2 className="lp-section-title">Up and running in minutes</h2>
        </div>
        <div className="lp-steps">
          {STEPS.map((s, i) => (
            <div key={s.n} className="lp-step lp-reveal" style={{ '--si': i }}>
              <div className="lp-step-num">{s.n}</div>
              <h3 className="lp-step-title">{s.title}</h3>
              <p className="lp-step-desc">{s.desc}</p>
              {i < STEPS.length - 1 && <div className="lp-step-line" aria-hidden="true" />}
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="lp-final lp-reveal">
        <div className="lp-final-inner">
          <div className="lp-final-blob" aria-hidden="true" />
          <p className="lp-eyebrow" style={{ color: 'rgba(255,255,255,0.6)' }}>Join the community</p>
          <h2 className="lp-final-title">Ready to declutter?</h2>
          <p className="lp-final-sub">List your first item today — it takes under a minute.</p>
          <button className="lp-btn-primary lp-btn-white" onClick={() => navigate('/login?tab=signup')}>
            Create free account
            <span className="lp-btn-arrow">→</span>
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <span>🎓 Student Marketplace · Made at IE Business School</span>
      </footer>
    </div>
  )
}
