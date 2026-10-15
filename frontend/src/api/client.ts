import type { Itinerary, ItineraryRequest } from "../types";
import { mockItinerary } from "./mock";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const USING_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

export class ApiError extends Error {}

export async function fetchItinerary(request: ItineraryRequest, signal?: AbortSignal): Promise<Itinerary> {
  if (USING_MOCK_API) return mockItinerary(request, signal);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/itinerary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError("Couldn't reach the itinerary service. Check your connection and try again.");
  }

  if (!response.ok) {
    // FastAPI puts error messages in `detail`.
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      // Body wasn't JSON; fall through to the generic message.
    }
    throw new ApiError(
      typeof detail === "string" ? detail : `The itinerary service returned an error (${response.status}). Try again.`,
    );
  }

  return (await response.json()) as Itinerary;
}
