import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import Logo from "../components/Logo";
import { BookmarkIcon, GoogleIcon, MailIcon } from "../components/icons";
import { useAuth } from "../auth/context";
import { safeNext, type LoginMode } from "../lib/auth";
import { supabase } from "../lib/supabase";

const MIN_PASSWORD = 8;

const input =
  "w-full rounded-[10px] border border-line bg-white px-3 py-2.5 text-[15px] outline-none placeholder:text-sub/70 focus:border-accent";
const primaryButton =
  "rounded-[10px] bg-accent px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60";
const secondaryButton =
  "flex items-center justify-center gap-2.5 rounded-[10px] border border-line bg-white px-4 py-2.5 text-sm font-semibold hover:border-sub disabled:cursor-not-allowed disabled:opacity-60";

/** `/login?next=&mode=signin|signup`: Google or email sign-in, then back to `next`. */
export default function LoginPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { enabled, loading, user } = useAuth();
  const next = safeNext(params.get("next"));
  const mode: LoginMode = params.get("mode") === "signup" ? "signup" : "signin";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  if (!enabled || !supabase) return <Navigate to="/" replace />;
  if (!loading && user) return <Navigate to={next} replace />;

  const client = supabase;
  const redirectTo = `${window.location.origin}${next}`;
  const savingTrip = new URL(next, window.location.origin).searchParams.get("save") === "1";
  const backPath = withoutSave(next);

  const setMode = (m: LoginMode) => {
    setError(null);
    setParams(
      (p) => {
        if (m === "signup") p.set("mode", "signup");
        else p.delete("mode");
        return p;
      },
      { replace: true },
    );
  };

  const google = async () => {
    setError(null);
    setBusy(true);
    const { error: err } = await client.auth.signInWithOAuth({ provider: "google", options: { redirectTo } });
    // On success the browser is already leaving for Google.
    if (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !password) {
      setError("Enter your email and password.");
      return;
    }
    if (mode === "signup" && password.length < MIN_PASSWORD) {
      setError(`Use a password of at least ${MIN_PASSWORD} characters.`);
      return;
    }
    setError(null);
    setBusy(true);
    if (mode === "signin") {
      const { error: err } = await client.auth.signInWithPassword({ email: trimmed, password });
      setBusy(false);
      if (err) setError(err.message);
      else navigate(next, { replace: true });
      return;
    }
    const { data, error: err } = await client.auth.signUp({ email: trimmed, password, options: { emailRedirectTo: redirectTo } });
    setBusy(false);
    if (err) setError(err.message);
    // A session means email confirmation is off for this project.
    else if (data.session) navigate(next, { replace: true });
    else setSentTo(trimmed);
  };

  const resend = async () => {
    if (!sentTo) return;
    setBusy(true);
    const { error: err } = await client.auth.resend({ type: "signup", email: sentTo, options: { emailRedirectTo: redirectTo } });
    setBusy(false);
    if (err) setError(err.message);
    else setResent(true);
  };

  return (
    <div className="min-h-dvh bg-canvas bg-[radial-gradient(900px_420px_at_50%_0%,#E6F6F3_0%,transparent_70%)]">
      <header className="mx-auto flex h-16 max-w-6xl items-center px-4 sm:px-10">
        <Logo />
      </header>

      <main className="grid justify-items-center px-4 pt-8 pb-16">
        <div className="grid w-full max-w-[420px] gap-[18px] rounded-2xl border border-line bg-white p-7 shadow-[0_18px_40px_-20px_rgb(15_23_42/0.25)] max-sm:p-5">
          {sentTo ? (
            <div className="grid justify-items-center gap-3.5 py-2 text-center">
              <span className="grid size-[52px] place-items-center rounded-full bg-accent-soft text-accent">
                <MailIcon size={24} />
              </span>
              <h1 className="font-display text-2xl font-bold tracking-tight">Check your email</h1>
              <p className="text-sm leading-relaxed text-sub">
                We sent a confirmation link to <b className="font-semibold text-ink">{sentTo}</b>. Open it to finish creating your account.
                {savingTrip ? " It brings you back to your trip and saves it." : ""}
              </p>
              {error && (
                <p role="alert" className="text-sm font-medium text-red-700">
                  {error}
                </p>
              )}
              <button type="button" onClick={resend} disabled={busy || resent} className={`${secondaryButton} mt-1.5 w-full`}>
                {resent ? "Email sent again" : "Resend email"}
              </button>
            </div>
          ) : (
            <>
              <div className="grid gap-1 text-center">
                <h1 className="font-display text-[26px] font-bold tracking-tight">{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
                <p className="text-sm text-sub">Save itineraries and open them on any device.</p>
              </div>

              {savingTrip && (
                <p className="flex items-center gap-2.5 rounded-[10px] border border-[#99e6d8] bg-[#f0fdfa] px-3 py-2.5 text-[13px] text-accent-hover">
                  <BookmarkIcon size={16} className="shrink-0" />
                  Your trip will be saved when you finish.
                </p>
              )}

              <div role="group" aria-label="Account" className="grid grid-cols-2 rounded-[10px] bg-track p-[3px] text-[13px] font-semibold">
                {(["signin", "signup"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={mode === m}
                    onClick={() => setMode(m)}
                    className={`rounded-lg py-[7px] ${mode === m ? "bg-white text-ink shadow-[0_1px_2px_rgb(21_26_30/0.12)]" : "text-sub hover:text-ink"}`}
                  >
                    {m === "signin" ? "Sign in" : "Create account"}
                  </button>
                ))}
              </div>

              <button type="button" onClick={google} disabled={busy} className={secondaryButton}>
                <GoogleIcon /> Continue with Google
              </button>

              <div className="flex items-center gap-3 text-xs text-sub" aria-hidden="true">
                <span className="h-px flex-1 bg-line" />
                or
                <span className="h-px flex-1 bg-line" />
              </div>

              <form onSubmit={submit} noValidate className="grid gap-3">
                <div className="grid gap-1">
                  <label htmlFor="email" className="text-xs font-semibold">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className={input}
                  />
                </div>
                <div className="grid gap-1">
                  <label htmlFor="password" className="text-xs font-semibold">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    autoComplete={mode === "signup" ? "new-password" : "current-password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === "signup" ? `At least ${MIN_PASSWORD} characters` : undefined}
                    className={input}
                  />
                </div>
                {error && (
                  <p role="alert" className="text-sm font-medium text-red-700">
                    {error}
                  </p>
                )}
                <button type="submit" disabled={busy} className={`${primaryButton} mt-1`}>
                  {mode === "signup" ? "Create account" : "Sign in"}
                </button>
              </form>
            </>
          )}
        </div>
        {backPath !== "/" && (
          <Link to={backPath} className="mt-[18px] text-[13px] font-semibold text-sub hover:text-ink">
            ← Back to your trip
          </Link>
        )}
      </main>
    </div>
  );
}

/** `next` without the `save` flag, for leaving without signing in. */
function withoutSave(next: string): string {
  const url = new URL(next, window.location.origin);
  url.searchParams.delete("save");
  return `${url.pathname}${url.search}`;
}
