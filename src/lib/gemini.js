import { CATEGORIES } from '../supabaseClient'

// Vision-capable models the app can use, ordered by free-tier quota (most headroom
// first). Easy to add/remove/reorder — the Sell page builds its dropdown from this list.
export const GEMINI_MODELS = [
  { id: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash Lite (recommended)' },
  { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { id: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
  { id: 'gemini-3.5-flash', label: 'Gemini 3.5 Flash' },
]
export const DEFAULT_GEMINI_MODEL = GEMINI_MODELS[0].id
// Back-compat alias for older imports.
export const GEMINI_MODEL = DEFAULT_GEMINI_MODEL

const ENDPOINT = (model) =>
  `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`

// Turn a File/Blob into a bare base64 string (no data: prefix).
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result || ''
      const comma = result.indexOf(',')
      resolve(comma >= 0 ? result.slice(comma + 1) : result)
    }
    reader.onerror = () => reject(new Error('Could not read the image file.'))
    reader.readAsDataURL(file)
  })
}

const PROMPT = `You are a used-goods appraiser for a student second-hand marketplace.
The item in the photo is USED and being resold by a student. Price it for the
SECOND-HAND market, NOT at the new/retail price.

Method (think before pricing):
1. Identify the item and, if visible, its brand/model and rough age/generation.
2. Estimate its NEW retail price.
3. Judge condition from the photo (wear, scratches, completeness, packaging): roughly
   "like new", "good", "fair", or "worn".
4. Apply realistic second-hand depreciation from the new price:
   - Electronics / calculators: typically resell at ~30-55% of new (they depreciate fast).
   - Furniture / appliances: ~30-50% of new.
   - Books & notes: ~25-50% of new.
   - Adjust within the range by condition (worse condition = lower).
   The recommended price must be clearly BELOW the new retail price.

Return ONLY a JSON object with these exact keys:
{"title","description","category","recommended_price","price_min","price_max","price_reason"}

Rules:
- title: the specific item you recognize — include brand/model if visible (max ~60 chars).
- description: 1-2 friendly sentences about the item and its visible condition.
- category: pick EXACTLY one of: ${CATEGORIES.join(', ')}.
- recommended_price: the realistic USED resale price in euros, as a plain number (below new retail).
- price_min and price_max: a sensible used-market range (price_min <= recommended_price <= price_max), plain euro numbers, no currency symbol.
- price_reason: one short sentence citing the condition and that this is a second-hand price (e.g. "Good condition, priced ~40% below new").
Return only the JSON, nothing else.`

// Call ONE model. Throws on failure; rate-limit (429) errors are flagged so the
// caller can fall back to another model.
async function callModel(imageFile, apiKey, model) {
  const base64 = await fileToBase64(imageFile)
  const mimeType = imageFile.type || 'image/jpeg'

  const body = {
    contents: [
      {
        parts: [
          { inline_data: { mime_type: mimeType, data: base64 } },
          { text: PROMPT },
        ],
      },
    ],
    generationConfig: { response_mime_type: 'application/json' },
  }

  const res = await fetch(ENDPOINT(model), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = ''
    try {
      const err = await res.json()
      detail = err?.error?.message || ''
    } catch {
      /* ignore parse errors */
    }
    const error = new Error(`Gemini API error (${res.status}). ${detail}`.trim())
    if (res.status === 429) error.isRateLimit = true
    throw error
  }

  const data = await res.json()
  const text = (data?.candidates?.[0]?.content?.parts || [])
    .map((p) => p.text || '')
    .join('')
    .trim()

  if (!text) throw new Error('Gemini returned an empty response.')

  const cleaned = text
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim()

  let parsed
  try {
    parsed = JSON.parse(cleaned)
  } catch {
    throw new Error('Could not parse the AI response as JSON.')
  }

  return {
    title: parsed.title ?? '',
    description: parsed.description ?? '',
    category: CATEGORIES.includes(parsed.category) ? parsed.category : 'Other',
    recommended_price: parsed.recommended_price ?? '',
    price_min: parsed.price_min ?? '',
    price_max: parsed.price_max ?? '',
    price_reason: parsed.price_reason ?? '',
  }
}

/**
 * Recognize the item and recommend a price. Tries `preferredModel` first, then
 * automatically falls back to the other models in GEMINI_MODELS if it's rate-limited.
 * @returns the parsed fields plus `modelUsed` (the model that actually answered).
 */
export async function generateListingFromImage(imageFile, apiKey, preferredModel = DEFAULT_GEMINI_MODEL) {
  if (!apiKey) throw new Error('No Gemini API key provided.')
  if (!imageFile) throw new Error('Upload a photo first.')

  const order = [
    preferredModel,
    ...GEMINI_MODELS.map((m) => m.id).filter((id) => id !== preferredModel),
  ]

  let lastError
  for (const model of order) {
    try {
      const data = await callModel(imageFile, apiKey, model)
      return { ...data, modelUsed: model }
    } catch (err) {
      lastError = err
      // Only fall through on rate-limit; surface real errors (bad key, bad JSON) at once.
      if (err.isRateLimit) continue
      throw err
    }
  }
  throw new Error(
    `All models are rate-limited right now — try again later or add billing. ${lastError?.message || ''}`.trim(),
  )
}
