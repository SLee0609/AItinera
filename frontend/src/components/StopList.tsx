import StopChips from "./StopChips";
import TruncatedText from "./TruncatedText";
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
              className="row-span-2 grid size-6 place-items-center rounded-[7px] text-xs font-bold text-white"
              style={{ background: color }}
              aria-hidden="true"
            >
              {i + 1}
            </span>
            <h4 className="min-w-0 text-sm font-semibold">
              {compact ? <TruncatedText text={stop.name} className="block" /> : stop.name}
            </h4>
            <p className="col-[2/-1] min-w-0 text-xs leading-snug text-sub">
              {compact ? (leg ? `Then ${leg.durationMinutes} min ${modePhrase}` : "Last stop") : stop.description}
            </p>
          </>
        );
        const selected = selectedIndex === i;
        // The body is a subgrid spanning the whole row: the name shares the first line with the chips,
        // and the description below runs under them to the full width.
        const bodyClass = "col-[1/-1] row-[1/span_2] grid grid-cols-subgrid grid-rows-subgrid items-start gap-x-2.5 text-left";
        return (
          <li key={stop.placeId}>
            {/* The chips hold a link, which can't nest in the button, so they overlay its top-right
                cell instead. The row handles the click so the chips select too; the button's own
                clicks (including Enter and Space) bubble up to it. */}
            <div
              onClick={onSelect && (() => onSelect(i))}
              className={`grid grid-cols-[26px_minmax(0,1fr)_auto] gap-x-2.5 rounded-lg px-1 py-2 ${compact ? "" : "gap-y-1"} ${onSelect ? "cursor-pointer hover:bg-black/[0.03]" : ""} ${selected ? "bg-black/[0.04]" : ""}`}
            >
              {onSelect ? (
                <button type="button" aria-current={selected ? "true" : undefined} className={bodyClass}>
                  {body}
                </button>
              ) : (
                <div className={bodyClass}>{body}</div>
              )}
              <StopChips stop={stop} className="col-start-3 row-start-1" />
            </div>
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
