import { createContext, useContext } from "react";
import type { User } from "@supabase/supabase-js";

export interface AuthState {
  /** False when Supabase isn't configured; account features are hidden. */
  enabled: boolean;
  /** True until the stored session (or one in the URL after a sign-in redirect) has been read. */
  loading: boolean;
  user: User | null;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthState>({
  enabled: false,
  loading: false,
  user: null,
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

/** Name to show for a user: the Google profile name, else the email address. */
export function displayName(user: User): string {
  const meta = user.user_metadata as { full_name?: unknown; name?: unknown };
  const name = typeof meta.full_name === "string" ? meta.full_name : typeof meta.name === "string" ? meta.name : "";
  return name.trim() || user.email || "Account";
}

/** One or two initials for the avatar: "Alex Kim" -> "AK", "alex@example.com" -> "A". */
export function initials(name: string): string {
  const words = name.includes("@") ? [name] : name.split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return letters.map((w) => w[0]?.toUpperCase() ?? "").join("") || "?";
}
