import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router";
import AccountNav from "../components/AccountNav";
import Logo from "../components/Logo";
import Toast, { type ToastMessage } from "../components/Toast";
import { ArrowRightIcon, BookmarkIcon, ChevronRightIcon, PinIcon, TrashIcon } from "../components/icons";
import { listSaved, unsaveItinerary } from "../api/client";
import { useAuth } from "../auth/context";
import { loginUrl } from "../lib/auth";
import { formatTravel, pluralDays } from "../lib/format";
import { travelSavings, tripUrl } from "../lib/itinerary";
import type { SavedItinerarySummary } from "../types";

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; trips: SavedItinerarySummary[] };

const savedDate = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

/** `/saved`: the signed-in user's saved itineraries, newest first. */
export default function SavedPage() {
  const { enabled, loading, user } = useAuth();

  if (!enabled) return <Navigate to="/" replace />;
  if (!loading && !user) return <Navigate to={loginUrl("/saved")} replace />;

  return (
    <div className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-20 flex items-center gap-7 border-b border-line bg-white px-4 py-3 sm:px-10 md:h-16 md:py-0">
        <Logo />
        <div className="ml-auto flex items-center gap-2.5">
          <Link to="/" className="rounded-[10px] bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink/85">
            New trip
          </Link>
          <span aria-hidden="true" className="h-6 w-px bg-line" />
          <AccountNav />
        </div>
      </header>
      {/* Keyed by user so signing in as someone else reloads the list. */}
      {user ? <SavedList key={user.id} /> : <Spinner />}
    </div>
  );
}

function SavedList() {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [removing, setRemoving] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const clearToast = useCallback(() => setToast(null), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    listSaved(controller.signal)
      .then((trips) => setState({ status: "success", trips }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: err instanceof Error ? err.message : "Something went wrong. Try again." });
      });
    return () => controller.abort();
  }, [attempt]);

  const remove = async (trip: SavedItinerarySummary) => {
    setRemoving(trip.id);
    try {
      await unsaveItinerary(trip.id);
      setState((s) => (s.status === "success" ? { ...s, trips: s.trips.filter((t) => t.id !== trip.id) } : s));
      setToast({ text: `Removed ${trip.city}`, tone: "success" });
    } catch (err) {
      setToast({ text: err instanceof Error ? err.message : "Couldn't remove it. Try again.", tone: "error" });
    } finally {
      setRemoving(null);
    }
  };

  return (
    <main className="mx-auto grid max-w-[880px] gap-5 px-4 pt-10 pb-16 sm:px-10">
      <div className="grid gap-0.5">
        <h1 className="font-display text-[32px] font-bold tracking-tight">Saved itineraries</h1>
        {state.status === "success" && state.trips.length > 0 && (
          <p className="text-sm text-sub">
            {state.trips.length} {state.trips.length === 1 ? "trip saved" : "trips saved"}
          </p>
        )}
      </div>

      {state.status === "loading" && <Spinner />}

      {state.status === "error" && (
        <div className="grid justify-items-center gap-1 py-16 text-center" role="alert">
          <p className="font-display text-xl font-bold">Couldn't load your trips</p>
          <p className="max-w-md text-sm text-sub">{state.message}</p>
          <button
            type="button"
            onClick={() => setAttempt((n) => n + 1)}
            className="mt-4 rounded-[10px] bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
          >
            Try again
          </button>
        </div>
      )}

      {state.status === "success" && state.trips.length === 0 && (
        <div className="grid justify-items-center gap-2.5 rounded-2xl border border-dashed border-[#d4d6d1] bg-white px-6 py-16 text-center">
          <span className="grid size-[52px] place-items-center rounded-full bg-track text-sub" aria-hidden="true">
            <BookmarkIcon size={22} />
          </span>
          <p className="mt-1.5 font-display text-xl font-bold">No saved trips yet</p>
          <p className="max-w-[360px] text-sm leading-normal text-sub">
            Plan a trip and click Save to keep it here.
          </p>
          <Link to="/" className="mt-2 flex items-center gap-2 rounded-[10px] bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover">
            Plan a trip <ArrowRightIcon size={16} />
          </Link>
        </div>
      )}

      {state.status === "success" && state.trips.length > 0 && (
        <ul className="grid gap-2.5">
          {state.trips.map((trip) => {
            const savings = travelSavings(trip.optimizedTravelMinutes, trip.naiveTravelMinutes);
            return (
              <li key={trip.id} className="flex items-center gap-2 rounded-[14px] border border-line bg-white py-1.5 pr-2.5 pl-1.5">
                <Link to={tripUrl(trip.id)} className="flex min-w-0 flex-1 items-center gap-4 rounded-[10px] px-3.5 py-3 hover:bg-canvas max-sm:gap-3 max-sm:px-2">
                  <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent max-sm:hidden" aria-hidden="true">
                    <PinIcon size={20} />
                  </span>
                  <span className="grid min-w-0 flex-1 gap-[3px]">
                    <span className="truncate font-display text-[17px] font-bold">{trip.city}</span>
                    <span className="text-[13px] text-sub">
                      {pluralDays(trip.days)} · {trip.stopCount} stops · {formatTravel(trip.optimizedTravelMinutes)} of travel
                    </span>
                  </span>
                  <span className="grid shrink-0 justify-items-end gap-[3px]">
                    {savings.percent > 0 && (
                      <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-bold text-accent-ink">{savings.percent}% less travel</span>
                    )}
                    <span className="text-xs text-sub">Saved {savedDate.format(new Date(trip.savedAt))}</span>
                  </span>
                  <ChevronRightIcon size={18} className="shrink-0 text-sub max-sm:hidden" />
                </Link>
                <button
                  type="button"
                  onClick={() => remove(trip)}
                  disabled={removing === trip.id}
                  aria-label={`Remove ${trip.city} from saved`}
                  title="Remove"
                  className="grid size-10 shrink-0 place-items-center rounded-[10px] text-sub hover:bg-canvas hover:text-red-700 disabled:opacity-50"
                >
                  <TrashIcon size={17} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <Toast message={toast} onDone={clearToast} />
    </main>
  );
}

function Spinner() {
  return (
    <div className="grid place-items-center py-24" role="status" aria-label="Loading">
      <span className="size-9 animate-spin rounded-full border-[3px] border-track border-t-accent" aria-hidden="true" />
    </div>
  );
}
