export type LoginMode = "signin" | "signup";

/**
 * The `next` parameter of the login page, if it's a path on this site. Anything else (another origin,
 * a protocol-relative `//host` URL, a backslash trick) falls back to the home page.
 */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return "/";
  return next;
}

export function loginUrl(next: string, mode: LoginMode = "signin") {
  const params = new URLSearchParams({ next });
  if (mode === "signup") params.set("mode", "signup");
  return `/login?${params}`;
}

/** Path to return to after signing in from a trip's Save button: the trip, which then saves itself. */
export const saveAfterLoginPath = (tripPath: string) => `${tripPath}${tripPath.includes("?") ? "&" : "?"}save=1`;

/** Where a password reset email sends people: the reset page, which then continues to `next`. */
export const resetPasswordUrl = (next: string) => `/reset-password?${new URLSearchParams({ next })}`;

/**
 * The error Supabase puts in the URL fragment when a reset or confirmation link is invalid or expired,
 * such as `#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired`.
 */
export function linkError(hash: string): string | null {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  if (!params.get("error") && !params.get("error_code")) return null;
  const description = params.get("error_description")?.trim();
  if (!description) return "This link is invalid or has expired.";
  return /[.!?]$/.test(description) ? description : `${description}.`;
}
