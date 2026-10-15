import CompareBars from "./CompareBars";
import { ClockIcon, RouteIcon } from "./icons";
import { formatTravel } from "../lib/format";
import { travelSavings } from "../lib/itinerary";
import type { Itinerary } from "../types";

const tile = "grid content-start gap-0.5 rounded-[14px] border border-line bg-white px-[18px] py-3.5";
const tileLabel = "flex items-center gap-1.5 text-[12.5px] font-semibold text-sub";

export default function StatTiles({ itinerary }: { itinerary: Itinerary }) {
  const { optimizedTravelMinutes: optimized, naiveTravelMinutes: naive } = itinerary;
  const stopCount = itinerary.dayPlans.reduce((n, d) => n + d.stops.length, 0);
  const savings = travelSavings(optimized, naive);

  return (
    <section aria-label="Travel time" className="grid gap-3.5 md:grid-cols-[1fr_1fr_1.25fr]">
      <div className={tile}>
        <span className={tileLabel}>
          <RouteIcon size={14} /> Optimized travel time
        </span>
        <span className="font-display text-3xl font-bold tracking-tight text-accent tabular-nums">{formatTravel(optimized)}</span>
        <span className="text-[12.5px] text-sub">
          Across {itinerary.dayPlans.length} days, between {stopCount} stops
        </span>
      </div>
      <div className={tile}>
        <span className={tileLabel}>
          <ClockIcon size={14} /> Unoptimized order
        </span>
        <span className="font-display text-3xl font-bold tracking-tight text-sub tabular-nums">{formatTravel(naive)}</span>
        <span className="text-[12.5px] text-sub">Same stops in the order first suggested</span>
      </div>
      <div className={`${tile} gap-2`}>
        <span className={tileLabel}>
          {savings.minutes > 0
            ? `You save ${formatTravel(savings.minutes)} of travel · ${savings.percent}% less`
            : "The suggested order was already the fastest"}
        </span>
        <CompareBars optimized={optimized} naive={naive} />
      </div>
    </section>
  );
}
