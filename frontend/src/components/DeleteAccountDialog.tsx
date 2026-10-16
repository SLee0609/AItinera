import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import Dialog from "./Dialog";
import { deleteAccount } from "../api/client";
import { supabase } from "../lib/supabase";

const CONFIRM_WORD = "delete";

/** Warns about what account deletion removes, and asks the user to type a word to confirm. */
export default function DeleteAccountDialog({ open, onClose, email }: { open: boolean; onClose: () => void; email?: string }) {
  const navigate = useNavigate();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirmed = typed.trim().toLowerCase() === CONFIRM_WORD;

  const close = () => {
    if (busy) return;
    setTyped("");
    setError(null);
    onClose();
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!confirmed) return;
    setBusy(true);
    setError(null);
    try {
      await deleteAccount();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't delete your account. Try again.");
      setBusy(false);
      return;
    }
    // The account is gone on the server; clear this browser's session without calling the server again.
    navigate("/", { replace: true });
    await supabase?.auth.signOut({ scope: "local" });
  };

  return (
    <Dialog open={open} onClose={close} title="Delete your account?">
      <div className="grid gap-3 text-sm leading-normal">
        <p>
          This permanently deletes your account{email ? <> (<b className="font-semibold">{email}</b>)</> : null} and your list of saved
          itineraries. <b className="font-semibold">This can't be undone.</b>
        </p>
        <p className="text-sub">
          Itineraries you generated aren't deleted: share links you've sent keep working, and other people who saved them keep them.
        </p>
      </div>
      <form onSubmit={submit} className="grid gap-3">
        <div className="grid gap-1">
          <label htmlFor="delete-confirm" className="text-xs font-semibold">
            Type <span className="font-mono">{CONFIRM_WORD}</span> to confirm
          </label>
          <input
            id="delete-confirm"
            type="text"
            autoComplete="off"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            className="w-full rounded-[10px] border border-line bg-white px-3 py-2.5 text-[15px] outline-none focus:border-red-700"
          />
        </div>
        {error && (
          <p role="alert" className="text-sm font-medium text-red-700">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2.5">
          <button
            type="button"
            onClick={close}
            disabled={busy}
            className="rounded-[10px] border border-line bg-white px-4 py-2 text-sm font-semibold hover:border-sub disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!confirmed || busy}
            className="rounded-[10px] bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Deleting…" : "Delete account"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
