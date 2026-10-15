import { formatTravel } from "../lib/format";

interface CompareBarsProps {
  optimized: number;
  naive: number;
  color?: string;
}

/** Two bars on the same scale: optimized travel time against the unoptimized order. */
export default function CompareBars({ optimized, naive, color = "var(--color-accent)" }: CompareBarsProps) {
  const max = Math.max(optimized, naive, 1);
  const rows = [
    { label: "Optimized", minutes: optimized, fill: color },
    { label: "Unoptimized", minutes: naive, fill: "var(--color-naive)" },
  ];
  return (
    <div className="grid gap-2">
      {rows.map((row) => (
        <div key={row.label} className="grid grid-cols-[84px_1fr_60px] items-center gap-2.5 text-[12.5px] text-sub tabular-nums">
          <span>{row.label}</span>
          <span className="h-2.5 overflow-hidden rounded-full bg-track">
            <span className="block h-full rounded-full" style={{ width: `${(row.minutes / max) * 100}%`, background: row.fill }} />
          </span>
          <b className="text-right font-semibold text-ink">{formatTravel(row.minutes)}</b>
        </div>
      ))}
    </div>
  );
}
