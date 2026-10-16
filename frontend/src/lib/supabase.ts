import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

/** Supabase client for sign-in only; data goes through the backend. Null when accounts aren't configured. */
export const supabase = url && publishableKey ? createClient(url, publishableKey) : null;

/** The current access token, refreshed by Supabase if it has expired. */
export async function accessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
