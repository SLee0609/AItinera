/**
 * Shapes exchanged with the FastAPI backend (`/api/itinerary`, `/api/saved`).
 * The backend serializes these fields in camelCase.
 */

export interface ItineraryRequest {
  city: string;
  days: number;
}

/** Google Routes API travel modes. */
export type TravelMode = "DRIVE" | "WALK" | "BICYCLE" | "TRANSIT";

export interface LatLng {
  lat: number;
  lng: number;
}

export interface Stop {
  placeId: string;
  name: string;
  description: string;
  visitMinutes: number;
  location: LatLng;
}

/** Travel from one stop to the next. `legs[i]` connects `stops[i]` and `stops[i + 1]`. */
export interface Leg {
  durationMinutes: number;
  /** Encoded polyline of the actual route, if the backend provides one. */
  polyline?: string;
}

export interface DayPlan {
  /** 1-based day number. */
  day: number;
  /** Short name for the day's area, such as "Louvre & the Islands". */
  title?: string;
  stops: Stop[];
  legs: Leg[];
  travelMinutes: number;
}

export interface Itinerary {
  /** Stored itinerary ID, used in share links (`/trip/:id`). Missing if the backend couldn't store it. */
  id?: string;
  /** Resolved destination name, such as "Paris, France". */
  city: string;
  travelMode: TravelMode;
  dayPlans: DayPlan[];
  optimizedTravelMinutes: number;
  /** Travel time for the same attractions in the order the LLM suggested them, cut into consecutive days. */
  naiveTravelMinutes: number;
}

/** One entry of `GET /api/saved`, newest first. */
export interface SavedItinerarySummary {
  id: string;
  city: string;
  days: number;
  stopCount: number;
  /** ISO 8601 timestamp. */
  savedAt: string;
  optimizedTravelMinutes: number;
  naiveTravelMinutes: number;
}

export interface SavedStatus {
  saved: boolean;
}

export interface AccountDeletion {
  deleted: boolean;
}
