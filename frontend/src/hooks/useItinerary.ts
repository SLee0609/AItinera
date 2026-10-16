import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import type { Itinerary } from "../types";

export type ItineraryState =
  | { status: "loading" }
  | { status: "error"; message: string; httpStatus?: number }
  | { status: "success"; itinerary: Itinerary };

/**
 * Loads an itinerary with `load`, which runs again on retry. `initial`, if given, is shown without loading.
 * Callers key their component by what `load` fetches, so `load` itself is read only on mount and retry.
 */
export function useItinerary(load: (signal: AbortSignal) => Promise<Itinerary>, initial?: Itinerary) {
  const [state, setState] = useState<ItineraryState>(initial ? { status: "success", itinerary: initial } : { status: "loading" });
  const [attempt, setAttempt] = useState(initial ? -1 : 0);

  useEffect(() => {
    if (attempt < 0) return;
    const controller = new AbortController();
    setState({ status: "loading" });
    load(controller.signal)
      .then((itinerary) => setState({ status: "success", itinerary }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          message: err instanceof Error ? err.message : "Something went wrong. Try again.",
          httpStatus: err instanceof ApiError ? err.status : undefined,
        });
      });
    return () => controller.abort();
    // `load` is left out on purpose; see the doc comment.
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => Math.max(n, 0) + 1), []);
  return { state, retry };
}
