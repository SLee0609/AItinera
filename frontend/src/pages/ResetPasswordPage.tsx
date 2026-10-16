import { useState, type FormEvent } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import Logo from "../components/Logo";
import { CheckIcon } from "../components/icons";
import { useAuth } from "../auth/context";
import { linkError, loginUrl, safeNext } from "../lib/auth";
import { supabase } from "../lib/supabase";

const MIN_PASSWORD = 8;

const input =
  "w-full rounded-[10px] border border-line bg-white px-3 py-2.5 text-[15px] outline-none placeholder:text-sub/70 focus:border-accent";
const primaryButton =
  "rounded-[10px] bg-accent px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60";

/**
 * `/reset-password?next=`: where the password reset email lands. Supabase signs the user in from the link
 * (the token is in the URL fragment), and this page sets the new password on that session.
 */
export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const { enabled, loading, user } = useAuth();
  const next = safeNext(params.get("next"));
  // Read once: Supabase clears the fragment after handling it.
  const [urlError] = useState(() => linkError(window.location.hash));
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (!enabled || !supabase) return <Navigate to="/" replace />;
  const client = supabase;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD) {
      setError(`Use a password of at least ${MIN_PASSWORD} characters.`);
      return;
    }
    if (password !== confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setError(null);
    setBusy(true);
    const { error: err } = await client.auth.updateUser({ password });
    setBusy(false);
    if (err) setError(err.message);
    else setDone(true);
  };

  let body;
  if (loading) {
    body = (
      <div className="grid place-items-center py-10" role="status" aria-label="Loading">
        <span className="size-9 animate-spin rounded-full border-[3px] border-track border-t-accent" aria-hidden="true" />
      </div>
    );
  } else if (done) {
    body = (
      <div className="grid justify-items-center gap-3.5 py-2 text-center">
        <span className="grid size-[52px] place-items-center rounded-full bg-accent-soft text-accent">
          <CheckIcon size={24} strokeWidth={2.4} />
        </span>
        <h1 className="font-display text-2xl font-bold tracking-tight">Password updated</h1>
        <p className="text-sm text-sub">You're signed in. Use your new password next time you sign in with email.</p>
        <Link to={next} replace className={`${primaryButton} mt-1.5 w-full`}>
          Continue
        </Link>
      </div>
    );
  } else if (!user) {
    body = (
      <div className="grid justify-items-center gap-3 py-2 text-center" role="alert">
        <h1 className="font-display text-2xl font-bold tracking-tight">This link doesn't work</h1>
        <p className="text-sm text-sub">
          {urlError ?? "This password reset link is invalid or has expired."} Reset links work once and expire after an hour.
        </p>
        <Link to={loginUrl(next)} className={`${primaryButton} mt-1.5 w-full`}>
          Request a new link
        </Link>
      </div>
    );
  } else {
    body = (
      <>
        <div className="grid gap-1 text-center">
          <h1 className="font-display text-[26px] font-bold tracking-tight">Set a new password</h1>
          <p className="text-sm text-sub">
            For <b className="font-semibold text-ink">{user.email}</b>
          </p>
        </div>
        <form onSubmit={submit} noValidate className="grid gap-3">
          <div className="grid gap-1">
            <label htmlFor="new-password" className="text-xs font-semibold">
              New password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={`At least ${MIN_PASSWORD} characters`}
              className={input}
            />
          </div>
          <div className="grid gap-1">
            <label htmlFor="confirm-password" className="text-xs font-semibold">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={input}
            />
          </div>
          {error && (
            <p role="alert" className="text-sm font-medium text-red-700">
              {error}
            </p>
          )}
          <button type="submit" disabled={busy} className={`${primaryButton} mt-1`}>
            {busy ? "Saving…" : "Save password"}
          </button>
        </form>
      </>
    );
  }

  return (
    <div className="min-h-dvh bg-canvas bg-[radial-gradient(900px_420px_at_50%_0%,#E6F6F3_0%,transparent_70%)]">
      <header className="mx-auto flex h-16 max-w-6xl items-center px-4 sm:px-10">
        <Logo />
      </header>
      <main className="grid justify-items-center px-4 pt-8 pb-16">
        <div className="grid w-full max-w-[420px] gap-[18px] rounded-2xl border border-line bg-white p-7 shadow-[0_18px_40px_-20px_rgb(15_23_42/0.25)] max-sm:p-5">
          {body}
        </div>
      </main>
    </div>
  );
}
