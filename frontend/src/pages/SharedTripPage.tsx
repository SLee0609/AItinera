import { useLocation, useParams } from "react-router";
import TripScreen from "../components/TripScreen";
import { getItinerary } from "../api/client";
import { useItinerary } from "../hooks/useItinerary";
import type { Itinerary } from "../types";

/** `/trip/:id`: a stored itinerary, exactly as it was generated. This is the share link. */
export default function SharedTripPage() {
  const { id = "" } = useParams();
  return <SharedTrip key={id} id={id} />;
}

function SharedTrip({ id }: { id: string }) {
  const location = useLocation();
  // Set by TripPage right after generating, so the trip shows without a second request.
  const passed = (location.state as { itinerary?: Itinerary } | null)?.itinerary;
  const { state, retry } = useItinerary((signal) => getItinerary(id, signal), passed?.id === id ? passed : undefined);

  return <TripScreen state={state} retry={retry} city="" loadingTitle="Opening itinerary" errorTitle="Couldn't open this trip" />;
}
