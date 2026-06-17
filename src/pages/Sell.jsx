import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase, PHOTO_BUCKET, CATEGORIES } from '../supabaseClient'
import { useAuth } from '../context/AuthContext'
import { generateListingFromImage, GEMINI_MODEL } from '../lib/gemini'
import Header from '../components/Header'

const DEFAULT_GEMINI_KEY = import.meta.env.VITE_GEMINI_API_KEY || ''

export default function Sell() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [imageFile, setImageFile]   = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [imageUrl, setImageUrl]     = useState('')
  const [geminiKey, setGeminiKey]   = useState(DEFAULT_GEMINI_KEY)
  const [form, setForm] = useState({
    title: '', description: '', category: CATEGORIES[0], price_min: '', price_max: '',
  })
  const [recommendation, setRecommendation] = useState(null)
  const [uploading, setUploading]   = useState(false)
  const [generating, setGenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [error, setError]           = useState('')

  // Separate refs: one triggers camera capture, one opens file picker
  const cameraInput = useRef(null)
  const uploadInput = useRef(null)

  function setField(key, value) { setForm(f => ({ ...f, [key]: value })) }

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setImageFile(file)
    setPreviewUrl(URL.createObjectURL(file))
    setImageUrl('')
    setRecommendation(null)
    setUploading(true)
    try {
      const ext  = file.name.split('.').pop() || 'jpg'
      const path = `${user.id}/${Date.now()}.${ext}`
      const { error: upErr } = await supabase.storage
        .from(PHOTO_BUCKET).upload(path, file, { cacheControl: '3600', upsert: false })
      if (upErr) throw upErr
      const { data } = supabase.storage.from(PHOTO_BUCKET).getPublicUrl(path)
      setImageUrl(data.publicUrl)
    } catch (err) {
      setError(`Image upload failed: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function handleGenerate() {
    setError('')
    if (!imageFile) { setError('Upload a photo first.'); return }
    setGenerating(true)
    try {
      const result = await generateListingFromImage(imageFile, geminiKey)
      setForm({
        title:       result.title       || '',
        description: result.description || '',
        category:    result.category    || CATEGORIES[0],
        price_min:   result.price_min   ?? '',
        price_max:   result.price_max   ?? '',
      })
      setRecommendation({
        title:             result.title             || '',
        recommended_price: result.recommended_price ?? '',
        price_min:         result.price_min         ?? '',
        price_max:         result.price_max         ?? '',
        price_reason:      result.price_reason      ?? '',
      })
    } catch (err) {
      setError(err.message || 'AI recognition failed.')
    } finally {
      setGenerating(false)
    }
  }

  async function handlePublish(e) {
    e.preventDefault()
    setError('')
    if (!imageUrl) { setError('Please upload a photo before publishing.'); return }
    setPublishing(true)
    try {
      const { error: insErr } = await supabase.from('listings').insert({
        user_id:     user.id,
        title:       form.title,
        description: form.description,
        category:    form.category,
        price_min:   form.price_min === '' ? null : Number(form.price_min),
        price_max:   form.price_max === '' ? null : Number(form.price_max),
        image_url:   imageUrl,
      })
      if (insErr) throw insErr
      navigate('/')
    } catch (err) {
      setError(`Could not publish: ${err.message}`)
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="app-page">
      <Header showSell={false} />
      <main className="app-container app-container-narrow">

        <div className="sell-header">
          <h1 className="sell-title">List an item</h1>
          <p className="sell-sub">Fill in the details below — or let AI do it from a photo.</p>
        </div>

        <form onSubmit={handlePublish} className="sell-form">

          {/* ── Step 1: Photo ── */}
          <div className="sell-block">
            <div className="sell-block-num">01</div>
            <h3 className="sell-block-title">Photo of your item</h3>
            <p className="sell-block-desc">Take a photo or upload one — this is the picture buyers see.</p>

            {/* Hidden inputs triggered by buttons below */}
            <input ref={cameraInput} type="file" accept="image/*" capture="environment"
              onChange={handleFileChange} hidden />
            <input ref={uploadInput} type="file" accept="image/*"
              onChange={handleFileChange} hidden />

            {previewUrl
              ? (
                <div className="sell-preview-wrap">
                  <img src={previewUrl} alt="preview" className="sell-preview-img" />
                  <button type="button" className="sell-preview-replace"
                    onClick={() => uploadInput.current?.click()}>
                    Replace photo
                  </button>
                </div>
              )
              : (
                <div className="sell-upload-buttons">
                  <button type="button" className="sell-upload-btn"
                    onClick={() => cameraInput.current?.click()}>
                    <span>📷</span> Take photo
                  </button>
                  <button type="button" className="sell-upload-btn sell-upload-btn--secondary"
                    onClick={() => uploadInput.current?.click()}>
                    <span>⬆️</span> Upload photo
                  </button>
                </div>
              )
            }

            {uploading && <p className="sell-status">⏳ Uploading photo…</p>}
            {imageUrl   && <p className="sell-status sell-status--ok">✓ Photo uploaded</p>}
          </div>

          {/* ── Step 2: AI ── */}
          <div className="sell-block">
            <div className="sell-block-num">02</div>
            <h3 className="sell-block-title">
              Recognize &amp; estimate price
              <span className="sell-block-badge">✨ Gemini {GEMINI_MODEL}</span>
            </h3>
            <p className="sell-block-desc">
              Let AI identify your item from the photo and suggest a fair selling price.
            </p>

            <label className="sell-label">
              Gemini API key
              <input
                type="password"
                className="sell-input"
                value={geminiKey}
                onChange={e => setGeminiKey(e.target.value)}
                placeholder="Paste a Gemini API key"
              />
            </label>

            <button
              type="button"
              className="sell-ai-btn"
              onClick={handleGenerate}
              disabled={generating || !imageFile}
            >
              {generating
                ? <><span className="sell-ai-spinner" /> Scanning photo…</>
                : <>🔍 Recognize &amp; suggest price</>
              }
            </button>

            {recommendation && (
              <div className="sell-estimate">
                <div className="sell-estimate-row">
                  <span className="sell-estimate-tag">Recognized</span>
                  <strong className="sell-estimate-item">{recommendation.title || 'Item'}</strong>
                </div>
                <div className="sell-estimate-price-row">
                  <span>Recommended price:</span>
                  <strong className="sell-estimate-price">
                    €{recommendation.recommended_price}
                  </strong>
                  {recommendation.price_min !== '' && recommendation.price_max !== '' && (
                    <span className="sell-estimate-range">
                      range €{recommendation.price_min}–{recommendation.price_max}
                    </span>
                  )}
                </div>
                {recommendation.price_reason && (
                  <p className="sell-estimate-reason">{recommendation.price_reason}</p>
                )}
                <p className="sell-estimate-hint">
                  Fields below were filled in for you — edit anything before publishing.
                </p>
              </div>
            )}
          </div>

          {/* ── Step 3: Details ── */}
          <div className="sell-block">
            <div className="sell-block-num">03</div>
            <h3 className="sell-block-title">Listing details</h3>

            <label className="sell-label">
              Title
              <input type="text" className="sell-input" value={form.title}
                onChange={e => setField('title', e.target.value)} required
                placeholder="e.g. TI-84 Plus Calculator — Excellent Condition" />
            </label>

            <label className="sell-label">
              Description
              <textarea className="sell-input" rows={3} value={form.description}
                onChange={e => setField('description', e.target.value)}
                placeholder="Describe the item's condition, what's included, etc." />
            </label>

            <label className="sell-label">
              Category
              <select className="sell-input" value={form.category}
                onChange={e => setField('category', e.target.value)}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>

            <div className="sell-row">
              <label className="sell-label">
                Price min (€)
                <input type="number" min="0" step="0.01" className="sell-input"
                  value={form.price_min} onChange={e => setField('price_min', e.target.value)}
                  placeholder="0" />
              </label>
              <label className="sell-label">
                Price max (€)
                <input type="number" min="0" step="0.01" className="sell-input"
                  value={form.price_max} onChange={e => setField('price_max', e.target.value)}
                  placeholder="0" />
              </label>
            </div>
          </div>

          {error && <p className="error" style={{ marginTop: 0 }}>{error}</p>}

          <div className="sell-actions">
            <button type="button" className="sell-cancel" onClick={() => navigate('/')}>
              Cancel
            </button>
            <button type="submit" className="sell-publish" disabled={publishing || uploading}>
              {publishing ? 'Publishing…' : 'Publish listing →'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
