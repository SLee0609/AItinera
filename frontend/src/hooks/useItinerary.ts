import { useCallback, useEffect, useState } from "react";
import { fetchItinerary } from "../api/client";
import type { Itinerary } from "../types";

export type ItineraryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; itinerary: Itinerary };

export function useItinerary(city: string, days: number) {
  const [state, setState] = useState<ItineraryState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    fetchItinerary({ city, days }, controller.signal)
      .then((itinerary) => setState({ status: "success", itinerary }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: err instanceof Error ? err.message : "Something went wrong. Try again." });
      });
    return () => controller.abort();
  }, [city, days, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}
