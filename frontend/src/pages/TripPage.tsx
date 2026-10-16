import { Link, Navigate, useSearchParams } from "react-router";
import ListView from "../components/ListView";
import MapView from "../components/MapView";
import TripHeader, { type TripView } from "../components/TripHeader";
import { USING_MOCK_API } from "../api/client";
import { useItinerary } from "../hooks/useItinerary";
import { pluralDays } from "../lib/format";
import { parseDays } from "../lib/itinerary";

// Loading and error states are centered like the landing page: the extra bottom padding (the
// header's height) puts them at the center of the screen.
const CENTERED = "grid flex-1 content-center justify-items-center px-4 pt-12 pb-28 text-center";

export default function TripPage() {
  const [params] = useSearchParams();
  const city = params.get("city")?.trim() ?? "";
  const days = parseDays(params.get("days"));

  if (!city || days === null) return <Navigate to="/" replace />;
  // Keyed so a new destination starts from a fresh loading state.
  return <Trip key={`${city}|${days}`} city={city} days={days} />;
}

function Trip({ city, days }: { city: string; days: number }) {
  const [params, setParams] = useSearchParams();
  const view: TripView = params.get("view") === "map" ? "map" : "list";
  const { state, retry } = useItinerary(city, days);

  const setView = (next: TripView) =>
    setParams(
      (p) => {
        p.set("view", next);
        return p;
      },
      { replace: true },
    );

  const itinerary = state.status === "success" ? state.itinerary : null;

  return (
    <div className={`bg-canvas ${!itinerary ? "flex min-h-dvh flex-col" : view === "map" ? "flex flex-col md:h-dvh" : "min-h-dvh"}`}>
      <TripHeader
        city={itinerary?.city ?? city}
        days={days}
        view={view}
        onViewChange={setView}
      />
      {USING_MOCK_API && (
        <p className="border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-center text-xs text-amber-900 sm:px-10">
          Showing the built-in Paris sample. Set VITE_USE_MOCK_API=false to use the backend.
        </p>
      )}

      {state.status === "loading" && (
        <div className={CENTERED} role="status">
          <span className="mb-5 size-9 animate-spin rounded-full border-[3px] border-track border-t-accent" aria-hidden="true" />
          <p className="font-display text-xl font-bold">
            Planning {pluralDays(days)} in {city}
          </p>
          <p className="mt-1 max-w-md text-sm text-sub">
            Picking attractions, verifying them, and optimizing routes. This can take up to a minute.
          </p>
        </div>
      )}

      {state.status === "error" && (
        <div className={CENTERED} role="alert">
          <p className="font-display text-xl font-bold">Couldn't plan this trip</p>
          <p className="mt-1 max-w-md text-sm text-sub">{state.message}</p>
          <div className="mt-5 flex gap-2.5">
            <button type="button" onClick={retry} className="rounded-[10px] bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover">
              Try again
            </button>
            <Link to="/" className="rounded-[10px] border border-line bg-white px-4 py-2 text-sm font-semibold hover:border-sub">
              Change trip
            </Link>
          </div>
        </div>
      )}

      {itinerary && (view === "list" ? <ListView itinerary={itinerary} /> : <MapView itinerary={itinerary} />)}
    </div>
  );
}
