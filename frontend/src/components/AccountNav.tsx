import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import DeleteAccountDialog from "./DeleteAccountDialog";
import { BookmarkIcon, ChevronIcon, LogOutIcon, TrashIcon } from "./icons";
import { displayName, initials, useAuth } from "../auth/context";
import { loginUrl } from "../lib/auth";

interface AccountNavProps {
  /** The landing page also offers "Create account" to guests and a "Saved trips" link to users. */
  variant?: "compact" | "full";
}

/** Header account control: Sign in for guests, an avatar menu for signed-in users. Hidden without Supabase. */
export default function AccountNav({ variant = "compact" }: AccountNavProps) {
  const { enabled, loading, user } = useAuth();
  const location = useLocation();
  if (!enabled) return null;

  if (loading) return <span className="size-[34px] rounded-full bg-track" aria-hidden="true" />;

  if (!user) {
    const here = location.pathname === "/login" ? "/" : `${location.pathname}${location.search}`;
    return (
      <div className="flex items-center gap-3">
        <Link to={loginUrl(here)} className="rounded-lg px-1 py-2 text-sm font-semibold hover:text-accent">
          Sign in
        </Link>
        {variant === "full" && (
          <Link
            to={loginUrl(here, "signup")}
            className="rounded-[10px] border border-line bg-white px-3.5 py-2 text-sm font-semibold hover:border-sub max-sm:hidden"
          >
            Create account
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3.5">
      {variant === "full" && (
        <Link to="/saved" className="flex items-center gap-1.5 rounded-lg px-1 py-2 text-sm font-semibold hover:text-accent max-sm:hidden">
          <BookmarkIcon size={15} /> Saved trips
        </Link>
      )}
      <AccountMenu />
    </div>
  );
}

function AccountMenu() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;
  const name = displayName(user);
  const itemClass = "flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium hover:bg-canvas";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 rounded-full p-0.5 text-sub hover:text-ink"
      >
        <span className="grid size-[34px] place-items-center rounded-full bg-accent text-[13px] font-bold text-white">{initials(name)}</span>
        <ChevronIcon size={14} />
      </button>
      {open && (
        <div role="menu" className="absolute top-full right-0 z-30 mt-2 grid w-60 rounded-xl border border-line bg-white p-1.5 shadow-[0_18px_40px_-12px_rgb(15_23_42/0.25)]">
          <div className="mb-1 grid border-b border-line px-3 pt-2 pb-3">
            <span className="truncate text-sm font-semibold">{name}</span>
            {user.email && user.email !== name && <span className="truncate text-[12.5px] text-sub">{user.email}</span>}
          </div>
          <Link role="menuitem" to="/saved" onClick={() => setOpen(false)} className={itemClass}>
            <BookmarkIcon size={16} /> Saved itineraries
          </Link>
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              void signOut();
            }}
            className={itemClass}
          >
            <LogOutIcon size={16} /> Sign out
          </button>
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              setDeleting(true);
            }}
            className={`${itemClass} mt-1 border-t border-line pt-2.5 text-red-700 hover:bg-red-50`}
          >
            <TrashIcon size={16} /> Delete account
          </button>
        </div>
      )}
      <DeleteAccountDialog open={deleting} onClose={() => setDeleting(false)} email={user.email} />
    </div>
  );
}
