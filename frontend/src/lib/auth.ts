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
