import { useEffect, useMemo } from "react";
import { AdvancedMarker, APIProvider, ControlPosition, InfoWindow, Map, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { formatVisit } from "../lib/format";
import { dayColor } from "../lib/itinerary";
import type { DayPlan, LatLng } from "../types";

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? "";
const MAP_ID = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID";
const DIM_OPACITY = 0.32;

export interface SelectedStop {
  day: number; // index into dayPlans
  stop: number; // index into that day's stops
}

interface ItineraryMapProps {
  dayPlans: DayPlan[];
  focusDay: number | null;
  selected: SelectedStop | null;
  onSelect: (selected: SelectedStop | null) => void;
  modePhrase: string;
}

export default function ItineraryMap(props: ItineraryMapProps) {
  if (!API_KEY) {
    return (
      <div className="grid h-full place-items-center bg-[#F1F2EE] p-8 text-center">
        <div className="grid max-w-sm gap-2">
          <p className="font-display text-lg font-bold">The map needs a Google Maps API key</p>
          <p className="text-sm text-sub">
            Set <code className="rounded bg-track px-1">VITE_GOOGLE_MAPS_API_KEY</code> in <code className="rounded bg-track px-1">frontend/.env.local</code>, then
            restart the dev server. The list view works without it.
          </p>
        </div>
      </div>
    );
  }
  return (
    <APIProvider apiKey={API_KEY}>
      <MapCanvas {...props} />
    </APIProvider>
  );
}

function MapCanvas({ dayPlans, focusDay, selected, onSelect, modePhrase }: ItineraryMapProps) {
  const first = dayPlans[0]?.stops[0]?.location ?? { lat: 0, lng: 0 };
  const selectedDay = selected ? dayPlans[selected.day] : null;
  const selectedStop = selected && selectedDay ? selectedDay.stops[selected.stop] : null;
  const nextLeg = selected && selectedDay ? selectedDay.legs[selected.stop] : undefined;
  const nextStop = selected && selectedDay ? selectedDay.stops[selected.stop + 1] : undefined;

  return (
    <Map
      mapId={MAP_ID}
      defaultCenter={first}
      defaultZoom={12}
      gestureHandling="greedy"
      disableDefaultUI
      zoomControl
      zoomControlOptions={{ position: ControlPosition.RIGHT_BOTTOM }}
      clickableIcons={false}
      onClick={() => onSelect(null)}
      className="h-full w-full"
    >
      <RouteLines dayPlans={dayPlans} focusDay={focusDay} />
      <FitBounds dayPlans={dayPlans} focusDay={focusDay} />

      {dayPlans.map((day, d) => {
        const dim = focusDay !== null && focusDay !== d;
        return day.stops.map((stop, s) => (
          <AdvancedMarker
            key={stop.placeId}
            position={stop.location}
            title={`Day ${day.day}, stop ${s + 1}: ${stop.name}`}
            zIndex={dim ? 1 : 10}
            onClick={() => onSelect({ day: d, stop: s })}
          >
            <PinGlyph color={dayColor(d)} label={s + 1} dim={dim} />
          </AdvancedMarker>
        ));
      })}

      {selected && selectedDay && selectedStop && (
        <InfoWindow
          position={selectedStop.location}
          pixelOffset={[0, -38]}
          onCloseClick={() => onSelect(null)}
          headerContent={<b className="font-sans text-sm font-semibold text-ink">{selectedStop.name}</b>}
        >
          <div className="grid gap-1 font-sans text-xs text-ink">
            <span>
              Day {selectedDay.day} · Stop {selected.stop + 1} · {formatVisit(selectedStop.visitMinutes)} visit
            </span>
            <span className="text-sub">
              {nextLeg && nextStop ? `Next: ${nextStop.name}, ${nextLeg.durationMinutes} min ${modePhrase}` : "Last stop of the day"}
            </span>
          </div>
        </InfoWindow>
      )}
    </Map>
  );
}

function PinGlyph({ color, label, dim }: { color: string; label: number; dim: boolean }) {
  return (
    <svg width="30" height="38" viewBox="0 0 30 38" style={{ opacity: dim ? DIM_OPACITY : 1, display: "block" }} aria-hidden="true">
      <path d="M15 37C11 28 2 23 2 14a13 13 0 1 1 26 0c0 9-9 14-13 23z" fill={color} stroke="#fff" strokeWidth="2" />
      <text x="15" y="18.5" textAnchor="middle" fontFamily="Public Sans, sans-serif" fontWeight="700" fontSize="12" fill="#fff">
        {label}
      </text>
    </svg>
  );
}

/** Draws each day's route: the encoded polyline per leg when available, otherwise straight segments. */
function RouteLines({ dayPlans, focusDay }: { dayPlans: DayPlan[]; focusDay: number | null }) {
  const map = useMap();
  const geometry = useMapsLibrary("geometry");

  useEffect(() => {
    if (!map) return;
    const lines: google.maps.Polyline[] = [];
    dayPlans.forEach((day, d) => {
      const dim = focusDay !== null && focusDay !== d;
      const path = day.legs.flatMap((leg, i): (google.maps.LatLng | LatLng)[] =>
        leg.polyline && geometry
          ? geometry.encoding.decodePath(leg.polyline)
          : [day.stops[i].location, day.stops[i + 1].location],
      );
      const opacity = dim ? DIM_OPACITY : 1;
      lines.push(
        new google.maps.Polyline({ map, path, clickable: false, strokeColor: "#FFFFFF", strokeWeight: 9, strokeOpacity: opacity, zIndex: dim ? 1 : 3 }),
        new google.maps.Polyline({ map, path, clickable: false, strokeColor: dayColor(d), strokeWeight: 5, strokeOpacity: opacity, zIndex: dim ? 2 : 4 }),
      );
    });
    return () => lines.forEach((line) => line.setMap(null));
  }, [map, geometry, dayPlans, focusDay]);

  return null;
}

/** Fits the map to the focused day's stops, or to the whole trip. */
function FitBounds({ dayPlans, focusDay }: { dayPlans: DayPlan[]; focusDay: number | null }) {
  const map = useMap();
  const points = useMemo(
    () => (focusDay === null ? dayPlans : [dayPlans[focusDay]]).flatMap((d) => d?.stops.map((s) => s.location) ?? []),
    [dayPlans, focusDay],
  );

  useEffect(() => {
    if (!map || points.length === 0) return;
    const bounds = new google.maps.LatLngBounds();
    points.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, { top: 90, right: 60, bottom: 170, left: 60 });
  }, [map, points]);

  return null;
}
