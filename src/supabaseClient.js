import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  // Fail loudly in dev rather than getting cryptic errors later.
  console.error(
    'Missing Supabase env vars. Copy .env.example to .env and fill in ' +
      'VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.',
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Public Storage bucket used for listing photos.
export const PHOTO_BUCKET = 'item-photos'

// Listing categories (shared by Feed filters and the Sell form).
export const CATEGORIES = [
  'Books & Notes',
  'Electronics',
  'Furniture',
  'Calculators',
  'Lab & Supplies',
  'Other',
]
