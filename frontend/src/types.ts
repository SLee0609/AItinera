/**
 * Shapes exchanged with the FastAPI backend (`POST /api/itinerary`).
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
  /** Travel time for this day's stops in their original, unoptimized order. */
  naiveTravelMinutes?: number;
}

export interface Itinerary {
  /** Resolved destination name, such as "Paris, France". */
  city: string;
  travelMode: TravelMode;
  dayPlans: DayPlan[];
  optimizedTravelMinutes: number;
  naiveTravelMinutes: number;
}
