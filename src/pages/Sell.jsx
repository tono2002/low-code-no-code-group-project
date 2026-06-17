import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase, PHOTO_BUCKET, CATEGORIES } from '../supabaseClient'
import { useAuth } from '../context/AuthContext'
import { generateListingFromImage, GEMINI_MODEL } from '../lib/gemini'
import Header from '../components/Header'

const DEFAULT_GEMINI_KEY = import.meta.env.VITE_GEMINI_API_KEY || ''

export default function Sell() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [imageFile, setImageFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [imageUrl, setImageUrl] = useState('') // public URL after upload

  const [geminiKey, setGeminiKey] = useState(DEFAULT_GEMINI_KEY)

  const [form, setForm] = useState({
    title: '',
    description: '',
    category: CATEGORIES[0],
    price_min: '',
    price_max: '',
  })

  const [uploading, setUploading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState('')

  function setField(key, value) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setImageFile(file)
    setPreviewUrl(URL.createObjectURL(file))
    setImageUrl('')

    // Upload immediately so the public URL is ready for publish.
    setUploading(true)
    try {
      const ext = file.name.split('.').pop() || 'jpg'
      const path = `${user.id}/${Date.now()}.${ext}`
      const { error: upErr } = await supabase.storage
        .from(PHOTO_BUCKET)
        .upload(path, file, { cacheControl: '3600', upsert: false })
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
    if (!imageFile) {
      setError('Upload a photo first.')
      return
    }
    setGenerating(true)
    try {
      const result = await generateListingFromImage(imageFile, geminiKey)
      setForm({
        title: result.title || '',
        description: result.description || '',
        category: result.category || CATEGORIES[0],
        price_min: result.price_min ?? '',
        price_max: result.price_max ?? '',
      })
    } catch (err) {
      setError(err.message || 'AI generation failed.')
    } finally {
      setGenerating(false)
    }
  }

  async function handlePublish(e) {
    e.preventDefault()
    setError('')
    if (!imageUrl) {
      setError('Please upload a photo before publishing.')
      return
    }
    setPublishing(true)
    try {
      const { error: insErr } = await supabase.from('listings').insert({
        user_id: user.id,
        title: form.title,
        description: form.description,
        category: form.category,
        price_min: form.price_min === '' ? null : Number(form.price_min),
        price_max: form.price_max === '' ? null : Number(form.price_max),
        image_url: imageUrl,
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
    <div className="page">
      <Header showSell={false} />
      <main className="container narrow">
        <h2>Sell an item</h2>

        <form onSubmit={handlePublish} className="form sell-form">
          {/* 1. Photo */}
          <section className="block">
            <h3>1. Photo</h3>
            <input type="file" accept="image/*" onChange={handleFileChange} />
            {uploading && <p className="muted">Uploading photo…</p>}
            {previewUrl && (
              <div className="preview">
                <img src={previewUrl} alt="preview" />
              </div>
            )}
            {imageUrl && <p className="notice">Photo uploaded ✓</p>}
          </section>

          {/* 2. AI */}
          <section className="block">
            <h3>2. Generate with AI</h3>
            <label>
              Gemini API key <span className="muted">(model: {GEMINI_MODEL})</span>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="Paste a Gemini API key"
              />
            </label>
            <button
              type="button"
              className="btn"
              onClick={handleGenerate}
              disabled={generating || !imageFile}
            >
              {generating ? 'Analyzing photo…' : '✨ Generate with AI'}
            </button>
          </section>

          {/* 3. Details */}
          <section className="block">
            <h3>3. Details</h3>
            <label>
              Title
              <input
                type="text"
                value={form.title}
                onChange={(e) => setField('title', e.target.value)}
                required
              />
            </label>
            <label>
              Description
              <textarea
                rows={3}
                value={form.description}
                onChange={(e) => setField('description', e.target.value)}
              />
            </label>
            <label>
              Category
              <select
                value={form.category}
                onChange={(e) => setField('category', e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <div className="row">
              <label>
                Price min (€)
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price_min}
                  onChange={(e) => setField('price_min', e.target.value)}
                />
              </label>
              <label>
                Price max (€)
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price_max}
                  onChange={(e) => setField('price_max', e.target.value)}
                />
              </label>
            </div>
          </section>

          {error && <p className="error">{error}</p>}

          <div className="actions">
            <button type="button" className="btn ghost" onClick={() => navigate('/')}>
              Cancel
            </button>
            <button type="submit" className="btn primary" disabled={publishing || uploading}>
              {publishing ? 'Publishing…' : 'Publish'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
