import { ClockIcon } from "./icons";
import { formatVisit } from "../lib/format";
import type { DayPlan } from "../types";

interface StopListProps {
  day: DayPlan;
  color: string;
  modePhrase: string;
  /** Compact rows show the next leg instead of the description (map sidebar). */
  compact?: boolean;
  selectedIndex?: number | null;
  onSelect?: (index: number) => void;
}

export default function StopList({ day, color, modePhrase, compact, selectedIndex, onSelect }: StopListProps) {
  return (
    <ol className="grid">
      {day.stops.map((stop, i) => {
        const leg = day.legs[i];
        const body = (
          <>
            <span
              className="grid size-6 place-items-center rounded-[7px] text-xs font-bold text-white"
              style={{ background: color }}
              aria-hidden="true"
            >
              {i + 1}
            </span>
            <div className="min-w-0">
              <h4 className="text-sm font-semibold">{stop.name}</h4>
              <p className="text-xs leading-snug text-sub">
                {compact ? (leg ? `Then ${leg.durationMinutes} min ${modePhrase}` : "Last stop") : stop.description}
              </p>
            </div>
            <span className="flex items-center gap-1 rounded-full bg-[#F1F3F2] px-2 py-0.5 text-[11.5px] font-semibold whitespace-nowrap text-[#3B4249]">
              <ClockIcon size={11} /> {formatVisit(stop.visitMinutes)}
            </span>
          </>
        );
        const rowClass = "grid w-full grid-cols-[26px_1fr_auto] items-start gap-2.5 rounded-lg px-1 py-2 text-left";
        return (
          <li key={stop.placeId}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(i)}
                aria-current={selectedIndex === i ? "true" : undefined}
                className={`${rowClass} hover:bg-black/[0.03] ${selectedIndex === i ? "bg-black/[0.04]" : ""}`}
              >
                {body}
              </button>
            ) : (
              <div className={rowClass}>{body}</div>
            )}
            {leg && !compact && (
              <div className="grid h-5 grid-cols-[26px_1fr] items-center gap-2.5 px-1 text-[11.5px] text-sub">
                <i className="mx-auto block h-full w-0.5 bg-line" aria-hidden="true" />
                <span>
                  {leg.durationMinutes} min {modePhrase}
                </span>
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
