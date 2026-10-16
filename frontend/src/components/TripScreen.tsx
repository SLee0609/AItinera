import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";
import Dialog from "./Dialog";
import ListView from "./ListView";
import MapView from "./MapView";
import Toast, { type ToastMessage } from "./Toast";
import TripHeader, { type TripView } from "./TripHeader";
import { BookmarkIcon } from "./icons";
import { USING_MOCK_API } from "../api/client";
import { useAuth } from "../auth/context";
import type { ItineraryState } from "../hooks/useItinerary";
import { useSaved } from "../hooks/useSaved";
import { loginUrl, saveAfterLoginPath } from "../lib/auth";
import { formatTravel, pluralDays } from "../lib/format";

// Loading and error states are centered like the landing page: the extra bottom padding (the
// header's height) puts them at the center of the screen.
const CENTERED = "grid flex-1 content-center justify-items-center px-4 pt-12 pb-28 text-center";

interface TripScreenProps {
  state: ItineraryState;
  retry: () => void;
  /** Shown while loading; the itinerary's resolved city replaces it. */
  city: string;
  days?: number;
  loadingTitle: string;
  loadingBody?: string;
  errorTitle: string;
}

/** Header, loading and error states, and the list or map view of one itinerary. */
export default function TripScreen({ state, retry, city, days, loadingTitle, loadingBody, errorTitle }: TripScreenProps) {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const auth = useAuth();
  const view: TripView = params.get("view") === "map" ? "map" : "list";
  const itinerary = state.status === "success" ? state.itinerary : null;
  const { saved, busy, setTo } = useSaved(itinerary?.id);
  const [guestDialog, setGuestDialog] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const clearToast = useCallback(() => setToast(null), []);

  const setView = (next: TripView) =>
    setParams(
      (p) => {
        p.set("view", next);
        return p;
      },
      { replace: true },
    );

  const changeSaved = useCallback(
    async (next: boolean) => {
      const error = await setTo(next);
      if (error) setToast({ text: error, tone: "error" });
      else if (next) setToast({ text: "Saved to your itineraries", tone: "success", link: { to: "/saved", label: "View all" } });
      else setToast({ text: "Removed from your itineraries", tone: "success" });
    },
    [setTo],
  );

  // Back from signing in through the Save button (`?save=1`): save the trip, then drop the parameter.
  const wantsSave = params.get("save") === "1";
  const autoSaved = useRef(false);
  useEffect(() => {
    if (!wantsSave || !itinerary?.id || auth.loading || !auth.user || autoSaved.current) return;
    autoSaved.current = true;
    void changeSaved(true);
    setParams(
      (p) => {
        p.delete("save");
        return p;
      },
      { replace: true },
    );
  }, [wantsSave, itinerary?.id, auth.loading, auth.user, changeSaved, setParams]);

  const onSaveClick = () => {
    if (!auth.user) setGuestDialog(true);
    else void changeSaved(!saved);
  };

  // Where the guest dialog sends people: back to this trip, minus any earlier save flag.
  const here = new URLSearchParams(location.search);
  here.delete("save");
  const query = here.toString();
  const tripPath = `${location.pathname}${query ? `?${query}` : ""}`;
  const next = saveAfterLoginPath(tripPath);
  const shownDays = itinerary ? itinerary.dayPlans.length : days;
  const stopCount = itinerary?.dayPlans.reduce((n, d) => n + d.stops.length, 0) ?? 0;
  const canRetry = state.status === "error" && state.httpStatus !== 404;

  return (
    <div className={`bg-canvas ${!itinerary ? "flex min-h-dvh flex-col" : view === "map" ? "flex flex-col md:h-dvh" : "min-h-dvh"}`}>
      <TripHeader
        city={itinerary?.city ?? city}
        days={shownDays}
        view={view}
        onViewChange={setView}
        itineraryId={itinerary?.id}
        save={auth.enabled ? { saved, busy: busy || auth.loading, onClick: onSaveClick } : undefined}
      />
      {USING_MOCK_API && (
        <p className="border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-center text-xs text-amber-900 sm:px-10">
          Showing the built-in Paris sample. Set VITE_USE_MOCK_API=false to use the backend.
        </p>
      )}

      {state.status === "loading" && (
        <div className={CENTERED} role="status">
          <span className="mb-5 size-9 animate-spin rounded-full border-[3px] border-track border-t-accent" aria-hidden="true" />
          <p className="font-display text-xl font-bold">{loadingTitle}</p>
          {loadingBody && <p className="mt-1 max-w-md text-sm text-sub">{loadingBody}</p>}
        </div>
      )}

      {state.status === "error" && (
        <div className={CENTERED} role="alert">
          <p className="font-display text-xl font-bold">{errorTitle}</p>
          <p className="mt-1 max-w-md text-sm text-sub">{state.message}</p>
          <div className="mt-5 flex gap-2.5">
            {canRetry && (
              <button type="button" onClick={retry} className="rounded-[10px] bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover">
                Try again
              </button>
            )}
            <Link
              to="/"
              className={
                canRetry
                  ? "rounded-[10px] border border-line bg-white px-4 py-2 text-sm font-semibold hover:border-sub"
                  : "rounded-[10px] bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
              }
            >
              {canRetry ? "Change trip" : "Plan a new trip"}
            </Link>
          </div>
        </div>
      )}

      {itinerary && (view === "list" ? <ListView itinerary={itinerary} /> : <MapView itinerary={itinerary} />)}

      {itinerary && (
        <Dialog open={guestDialog} onClose={() => setGuestDialog(false)} title="Save this trip">
          <div className="flex items-center gap-3 rounded-xl bg-canvas px-3.5 py-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-[10px] bg-accent-soft text-accent">
              <BookmarkIcon size={18} />
            </span>
            <div className="grid min-w-0">
              <span className="truncate text-sm font-semibold">
                {itinerary.city} · {pluralDays(itinerary.dayPlans.length)}
              </span>
              <span className="text-[12.5px] text-sub">
                {stopCount} stops · {formatTravel(itinerary.optimizedTravelMinutes)} of travel
              </span>
            </div>
          </div>
          <p className="text-sm leading-normal text-sub">
            Create a free account to keep this itinerary and open it again any time. We'll save it as soon as you're signed in.
          </p>
          <div className="grid gap-2">
            <Link
              to={loginUrl(next, "signup")}
              className="rounded-[10px] bg-accent px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-accent-hover"
            >
              Create account
            </Link>
            <Link to={loginUrl(next)} className="rounded-[10px] border border-line bg-white px-4 py-2.5 text-center text-sm font-semibold hover:border-sub">
              I already have an account
            </Link>
          </div>
        </Dialog>
      )}

      <Toast message={toast} onDone={clearToast} />
    </div>
  );
}
