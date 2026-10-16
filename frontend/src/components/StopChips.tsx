import { ClockIcon, ExternalIcon, GoogleMapsIcon } from "./icons";
import { formatVisit } from "../lib/format";
import { googleMapsUrl } from "../lib/itinerary";
import type { Stop } from "../types";

// White with a border, so the chips stay distinct on rows tinted by hover or selection.
const HALF = "flex h-[22px] items-center border bg-white";

/** The stop's visit time joined to a link that opens the place in Google Maps. */
export default function StopChips({ stop, className = "" }: { stop: Stop; className?: string }) {
  return (
    <span className={`flex shrink-0 items-center gap-[3px] text-[11.5px] font-semibold whitespace-nowrap text-[#3B4249] ${className}`}>
      <span className={`${HALF} gap-1 rounded-l-full border-line pr-2 pl-2.5`}>
        <ClockIcon size={11} /> {formatVisit(stop.visitMinutes)} visit
      </span>
      {/* The teal border and arrow mark this half as a link before it's hovered. */}
      <a
        href={googleMapsUrl(stop)}
        target="_blank"
        rel="noopener noreferrer"
        title="Open in Google Maps"
        aria-label={`Open ${stop.name} in Google Maps (opens in a new tab)`}
        // Opening Maps shouldn't also select the row it sits in.
        onClick={(e) => e.stopPropagation()}
        className={`${HALF} gap-0.5 rounded-r-full border-accent/45 pr-2 pl-1.5 text-accent hover:border-accent hover:bg-accent-soft/60`}
      >
        <GoogleMapsIcon size={14} />
        <ExternalIcon size={10} strokeWidth={2.5} />
      </a>
    </span>
  );
}
