import type { TravelMode } from "../types";

/** Travel time: "40 min", "2h 09m". */
export function formatTravel(minutes: number): string {
  const m = Math.round(minutes);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`;
}

/** Visit duration: "45m", "2h", "2h 30m". */
export function formatVisit(minutes: number): string {
  const m = Math.round(minutes);
  const h = Math.floor(m / 60);
  const rest = m % 60;
  if (h === 0) return `${rest}m`;
  return rest === 0 ? `${h}h` : `${h}h ${rest}m`;
}

const MODE_PHRASE: Record<TravelMode, string> = {
  TRANSIT: "by transit",
  WALK: "on foot",
  DRIVE: "by car",
  BICYCLE: "by bike",
};

const MODE_LABEL: Record<TravelMode, string> = {
  TRANSIT: "Transit",
  WALK: "Walking",
  DRIVE: "Driving",
  BICYCLE: "Cycling",
};

export const travelModePhrase = (mode: TravelMode) => MODE_PHRASE[mode];
export const travelModeLabel = (mode: TravelMode) => MODE_LABEL[mode];

export const pluralDays = (n: number) => `${n} ${n === 1 ? "day" : "days"}`;
