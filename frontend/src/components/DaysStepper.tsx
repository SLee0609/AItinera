import { MAX_DAYS, MIN_DAYS } from "../lib/itinerary";
import { pluralDays } from "../lib/format";

interface DaysStepperProps {
  id: string;
  value: number;
  onChange: (days: number) => void;
}

const stepButton =
  "grid size-7 place-items-center rounded-full border border-line text-base leading-none text-sub hover:border-sub hover:text-ink disabled:cursor-not-allowed disabled:opacity-40";

export default function DaysStepper({ id, value, onChange }: DaysStepperProps) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        className={stepButton}
        onClick={() => onChange(value - 1)}
        disabled={value <= MIN_DAYS}
        aria-label="Fewer days"
      >
        −
      </button>
      <output id={id} aria-live="polite" className="min-w-16 text-center text-[17px] font-medium tabular-nums">
        {pluralDays(value)}
      </output>
      <button
        type="button"
        className={stepButton}
        onClick={() => onChange(value + 1)}
        disabled={value >= MAX_DAYS}
        aria-label="More days"
      >
        +
      </button>
    </div>
  );
}
