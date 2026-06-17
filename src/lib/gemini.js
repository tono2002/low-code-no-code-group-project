import { CATEGORIES } from '../supabaseClient'

// Keep the model name in one place so it's easy to swap.
export const GEMINI_MODEL = 'gemini-2.5-flash'

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

/**
 * Send an image to Gemini: recognize the item and recommend a price.
 * @param {File|Blob} imageFile
 * @param {string} apiKey
 * @returns {Promise<{title,description,category,recommended_price,price_min,price_max,price_reason}>}
 */
export async function generateListingFromImage(imageFile, apiKey) {
  if (!apiKey) throw new Error('No Gemini API key provided.')
  if (!imageFile) throw new Error('Upload a photo first.')

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

  const res = await fetch(ENDPOINT(GEMINI_MODEL), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-goog-api-key': apiKey,
    },
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
    throw new Error(`Gemini API error (${res.status}). ${detail}`.trim())
  }

  const data = await res.json()
  const text = (data?.candidates?.[0]?.content?.parts || [])
    .map((p) => p.text || '')
    .join('')
    .trim()

  if (!text) throw new Error('Gemini returned an empty response.')

  // Strip any ``` or ```json fences just in case.
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
