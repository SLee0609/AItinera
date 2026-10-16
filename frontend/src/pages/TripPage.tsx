import { Navigate, useSearchParams } from "react-router";
import TripScreen from "../components/TripScreen";
import { fetchItinerary } from "../api/client";
import { useItinerary } from "../hooks/useItinerary";
import { pluralDays } from "../lib/format";
import { parseDays, tripUrl } from "../lib/itinerary";

/** `/trip?city=&days=`: generates a new itinerary, then moves to its share link (`/trip/:id`). */
export default function TripPage() {
  const [params] = useSearchParams();
  const city = params.get("city")?.trim() ?? "";
  const days = parseDays(params.get("days"));

  if (!city || days === null) return <Navigate to="/" replace />;
  // Keyed so a new destination starts from a fresh loading state.
  return <GeneratedTrip key={`${city}|${days}`} city={city} days={days} />;
}

function GeneratedTrip({ city, days }: { city: string; days: number }) {
  const [params] = useSearchParams();
  const { state, retry } = useItinerary((signal) => fetchItinerary({ city, days }, signal));

  // Stored itineraries live at their own URL, so refreshing or sharing shows the same trip.
  // The itinerary rides along in history state, so the next page doesn't fetch it again.
  if (state.status === "success" && state.itinerary.id) {
    const view = params.get("view") === "map" ? "map" : undefined;
    return <Navigate to={tripUrl(state.itinerary.id, view)} replace state={{ itinerary: state.itinerary }} />;
  }

  return (
    <TripScreen
      state={state}
      retry={retry}
      city={city}
      days={days}
      loadingTitle={`Planning ${pluralDays(days)} in ${city}`}
      loadingBody="Picking attractions, verifying them, and optimizing routes. This can take up to a minute."
      errorTitle="Couldn't plan this trip"
    />
  );
}
