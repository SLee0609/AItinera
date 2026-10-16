import type { DayPlan, Stop } from "../types";

export const MIN_DAYS = 1;
export const MAX_DAYS = 7;

/** One color per day, in order. Repeats if a trip is longer than the palette. */
const DAY_COLORS = ["#0F766E", "#4F46E5", "#C2610C", "#BE185D", "#0369A1", "#4D7C0F", "#7C3AED"];

export const dayColor = (index: number) => DAY_COLORS[index % DAY_COLORS.length];

export function travelSavings(optimized: number, naive: number) {
  const minutes = Math.max(0, naive - optimized);
  const percent = naive > 0 ? Math.round((minutes / naive) * 100) : 0;
  return { minutes, percent };
}

export const dayVisitMinutes = (day: DayPlan) => day.stops.reduce((sum, s) => sum + s.visitMinutes, 0);

export const dayTitle = (day: DayPlan) => (day.title ? `Day ${day.day} · ${day.title}` : `Day ${day.day}`);

/** Google Maps URL that opens the stop's exact place (Maps URLs API; no key needed). */
export const googleMapsUrl = (stop: Pick<Stop, "name" | "placeId">) =>
  `https://www.google.com/maps/search/?${new URLSearchParams({ api: "1", query: stop.name, query_place_id: stop.placeId })}`;

/** Parses the `days` query parameter, returning null when it is missing or out of range. */
export function parseDays(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value)) return null;
  const n = Number(value);
  return n >= MIN_DAYS && n <= MAX_DAYS ? n : null;
}

export function tripSearch(city: string, days: number, view?: "list" | "map") {
  const params = new URLSearchParams({ city, days: String(days) });
  if (view) params.set("view", view);
  return `/trip?${params}`;
}
