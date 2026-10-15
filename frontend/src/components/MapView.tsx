import { useState } from "react";
import CompareBars from "./CompareBars";
import ItineraryMap, { type SelectedStop } from "./ItineraryMap";
import StopList from "./StopList";
import { ChevronIcon } from "./icons";
import { formatTravel, formatVisit, pluralDays, travelModePhrase } from "../lib/format";
import { dayColor, dayTitle, dayVisitMinutes } from "../lib/itinerary";
import type { Itinerary } from "../types";

export default function MapView({ itinerary }: { itinerary: Itinerary }) {
  const { dayPlans } = itinerary;
  const modePhrase = travelModePhrase(itinerary.travelMode);
  const [focusDay, setFocusDay] = useState<number | null>(null);
  const [selected, setSelected] = useState<SelectedStop | null>(null);

  const focus = (day: number | null) => {
    setFocusDay(day);
    if (selected && selected.day !== day) setSelected(null);
  };
  const select = (s: SelectedStop | null) => {
    setSelected(s);
    if (s) setFocusDay(s.day);
  };

  const focused = focusDay !== null ? dayPlans[focusDay] : null;
  const cityShort = itinerary.city.split(",")[0];

  return (
    <main className="grid md:min-h-0 md:flex-1 md:grid-cols-[380px_1fr]">
      <aside className="grid grid-rows-[auto_1fr] border-line bg-white max-md:border-b md:overflow-hidden md:border-r">
        <div className="grid gap-2.5 border-b border-line px-5 py-4">
          <h2 className="font-display text-xl font-bold tracking-tight">
            {cityShort}, {pluralDays(dayPlans.length)}
          </h2>
          <CompareBars optimized={itinerary.optimizedTravelMinutes} naive={itinerary.naiveTravelMinutes} />
        </div>
        <div className="grid content-start gap-2 p-3 md:overflow-y-auto">
          {dayPlans.map((day, d) => {
            const color = dayColor(d);
            const open = focusDay === null || focusDay === d;
            const active = focusDay === d;
            return (
              <section
                key={day.day}
                className="rounded-xl border"
                style={{
                  borderColor: active ? color : "var(--color-line)",
                  boxShadow: active ? `0 0 0 3px color-mix(in srgb, ${color} 15%, transparent)` : undefined,
                }}
              >
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => focus(active ? null : d)}
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left font-semibold"
                >
                  <i className="block size-2.5 shrink-0 rounded-full" style={{ background: color }} aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate">{dayTitle(day)}</span>
                  <span className="text-xs font-medium text-sub">{formatTravel(day.travelMinutes)}</span>
                  <ChevronIcon size={16} className={`shrink-0 text-sub transition-transform ${open ? "rotate-180" : ""}`} />
                </button>
                {open && (
                  <div className="px-2 pb-2">
                    <StopList
                      day={day}
                      color={color}
                      modePhrase={modePhrase}
                      compact
                      selectedIndex={selected?.day === d ? selected.stop : null}
                      onSelect={(stop) => select({ day: d, stop })}
                    />
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </aside>

      <div className="relative h-[70dvh] overflow-hidden md:h-auto">
        <ItineraryMap dayPlans={dayPlans} focusDay={focusDay} selected={selected} onSelect={select} modePhrase={modePhrase} />

        <div role="group" aria-label="Show days" className="absolute top-4 left-4 flex flex-wrap gap-2 pr-4">
          {[null, ...dayPlans.map((_, d) => d)].map((d) => {
            const on = focusDay === d;
            return (
              <button
                key={d ?? "all"}
                type="button"
                aria-pressed={on}
                onClick={() => focus(d)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-semibold shadow-[0_2px_6px_rgb(15_23_42/0.08)] ${
                  on ? "border-ink bg-ink text-white" : "border-line bg-white text-ink hover:border-sub"
                }`}
              >
                {d !== null && <i className="block size-2 rounded-full" style={{ background: dayColor(d) }} aria-hidden="true" />}
                {d === null ? "All days" : `Day ${dayPlans[d].day}`}
              </button>
            );
          })}
        </div>

        <div className="absolute bottom-6 left-4 grid w-[min(330px,calc(100%-90px))] gap-2 rounded-[14px] bg-white px-4 py-3.5 shadow-[0_10px_30px_-10px_rgb(15_23_42/0.35)]">
          <div className="flex items-baseline justify-between">
            <span className="text-[12.5px] font-semibold text-sub">{focused ? `Day ${focused.day} travel` : "Total travel"}</span>
            <b className="font-display text-2xl font-bold tracking-tight text-accent">
              {formatTravel(focused ? focused.travelMinutes : itinerary.optimizedTravelMinutes)}
            </b>
          </div>
          {focused ? (
            <p className="text-[12.5px] text-sub">
              {focused.stops.length} stops · {formatVisit(dayVisitMinutes(focused))} at sights
            </p>
          ) : (
            <CompareBars optimized={itinerary.optimizedTravelMinutes} naive={itinerary.naiveTravelMinutes} />
          )}
        </div>
      </div>
    </main>
  );
}
