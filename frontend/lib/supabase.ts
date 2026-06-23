import { createClient } from "@supabase/supabase-js";

// NEXT_PUBLIC_* values are inlined at build time. On a configured build (e.g.
// Vercel) the real Supabase URL/key are baked in. The placeholder fallbacks
// below only apply when the env vars are absent (e.g. a local build with no
// .env): createClient() throws on an empty URL, which would break `next build`
// prerendering of /chart, so we fall back to a harmless local placeholder.
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://localhost:54321";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "public-anon-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
