import type { AccountDeletion, Itinerary, ItineraryRequest, SavedItinerarySummary, SavedStatus } from "../types";
import { accessToken } from "../lib/supabase";
import { mockItinerary } from "./mock";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const USING_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

export class ApiError extends Error {
  /** HTTP status, or 0 when the service couldn't be reached. */
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Calls the backend, sending the signed-in user's access token if there is one. */
async function request<T>(method: string, path: string, options: { body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const token = await accessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (err) {
    if (options.signal?.aborted) throw err;
    throw new ApiError("Couldn't reach the itinerary service. Check your connection and try again.", 0);
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
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function fetchItinerary(req: ItineraryRequest, signal?: AbortSignal): Promise<Itinerary> {
  if (USING_MOCK_API) return mockItinerary(req, signal);
  return request("POST", "/api/itinerary", { body: req, signal });
}

export const getItinerary = (id: string, signal?: AbortSignal) =>
  request<Itinerary>("GET", `/api/itinerary/${encodeURIComponent(id)}`, { signal });

export const listSaved = (signal?: AbortSignal) => request<SavedItinerarySummary[]>("GET", "/api/saved", { signal });

export const getSavedStatus = (id: string, signal?: AbortSignal) =>
  request<SavedStatus>("GET", `/api/saved/${encodeURIComponent(id)}`, { signal });

export const saveItinerary = (id: string) => request<SavedStatus>("PUT", `/api/saved/${encodeURIComponent(id)}`);

export const unsaveItinerary = (id: string) => request<SavedStatus>("DELETE", `/api/saved/${encodeURIComponent(id)}`);

/** Deletes the signed-in user's account. Itineraries they generated stay available through their share links. */
export const deleteAccount = () => request<AccountDeletion>("DELETE", "/api/account");
