import StatTiles from "./StatTiles";
import StopList from "./StopList";
import { formatTravel, formatVisit, travelModePhrase } from "../lib/format";
import { dayColor, dayTitle, dayVisitMinutes } from "../lib/itinerary";
import type { Itinerary } from "../types";

export default function ListView({ itinerary }: { itinerary: Itinerary }) {
  const modePhrase = travelModePhrase(itinerary.travelMode);
  return (
    <main className="mx-auto grid max-w-[1400px] gap-4 px-4 py-6 sm:px-10">
      <StatTiles itinerary={itinerary} />
      <div className="grid items-start gap-3.5 md:grid-cols-2 xl:grid-cols-3">
        {itinerary.dayPlans.map((day, i) => {
          const color = dayColor(i);
          return (
            <section key={day.day} aria-label={`Day ${day.day}`} className="overflow-hidden rounded-[14px] border border-line bg-white">
              <header className="grid gap-0.5 border-b border-line px-4 py-3">
                <h3 className="flex items-center gap-2 font-display text-[15px] font-bold">
                  <i className="block size-2.5 rounded-full" style={{ background: color }} aria-hidden="true" />
                  {dayTitle(day)}
                </h3>
                <p className="text-xs text-sub">
                  {formatVisit(dayVisitMinutes(day))} at sights · {formatTravel(day.travelMinutes)} travel time
                </p>
              </header>
              <div className="px-3 pt-2 pb-3">
                <StopList day={day} color={color} modePhrase={modePhrase} />
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
