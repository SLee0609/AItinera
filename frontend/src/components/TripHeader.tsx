import { useEffect, useState } from "react";
import { Link } from "react-router";
import AccountNav from "./AccountNav";
import Logo from "./Logo";
import { BookmarkIcon, CheckIcon, ListIcon, MapIcon, PinIcon, ShareIcon } from "./icons";
import { pluralDays } from "../lib/format";
import { tripUrl } from "../lib/itinerary";

export type TripView = "list" | "map";

interface SaveControl {
  saved: boolean | null;
  busy: boolean;
  onClick: () => void;
}

interface TripHeaderProps {
  city: string;
  days?: number;
  view: TripView;
  onViewChange: (view: TripView) => void;
  /** Stored itinerary ID; Share needs it. */
  itineraryId?: string;
  /** Omitted when accounts aren't configured. */
  save?: SaveControl;
}

const VIEWS: { value: TripView; label: string; Icon: typeof ListIcon }[] = [
  { value: "list", label: "List", Icon: ListIcon },
  { value: "map", label: "Map", Icon: MapIcon },
];

const outlineButton =
  "flex items-center gap-2 rounded-[10px] border border-line bg-white px-3.5 py-2 text-sm font-semibold hover:border-sub disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-line max-sm:p-2.5";

export default function TripHeader({ city, days, view, onViewChange, itineraryId, save }: TripHeaderProps) {
  const [shareState, setShareState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (shareState === "idle") return;
    const t = setTimeout(() => setShareState("idle"), 2000);
    return () => clearTimeout(t);
  }, [shareState]);

  const share = async () => {
    if (!itineraryId) return;
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${tripUrl(itineraryId)}`);
      setShareState("copied");
    } catch {
      setShareState("failed");
    }
  };

  const unavailable = itineraryId ? undefined : "This trip couldn't be stored, so it can't be shared or saved.";
  const isSaved = save?.saved === true;

  return (
    <header className="sticky top-0 z-20 flex flex-wrap items-center gap-x-7 gap-y-2 border-b border-line bg-white px-4 py-3 sm:px-10 md:h-16 md:py-0">
      <Logo />
      {city && (
        <div className="flex min-w-0 items-center gap-2 text-sm text-sub max-md:order-last max-md:w-full">
          <PinIcon size={15} className="shrink-0" />
          <span className="truncate">
            <b className="font-semibold text-ink">{city}</b>
            {days !== undefined && ` · ${pluralDays(days)}`}
          </span>
        </div>
      )}
      <div className="ml-auto flex flex-wrap items-center justify-end gap-2.5">
        <div role="group" aria-label="Itinerary view" className="flex rounded-[10px] bg-track p-[3px] text-[13px] font-semibold">
          {VIEWS.map(({ value, label, Icon }) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              onClick={() => onViewChange(value)}
              className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 max-sm:px-2.5 ${
                view === value ? "bg-white text-ink shadow-[0_1px_2px_rgb(21_26_30/0.12)]" : "text-sub hover:text-ink"
              }`}
            >
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>
        {save && (
          <button
            type="button"
            onClick={save.onClick}
            disabled={!itineraryId || save.busy}
            title={unavailable}
            aria-pressed={isSaved}
            className={isSaved ? `${outlineButton} border-[#99e6d8] bg-accent-soft text-accent-ink hover:border-accent` : outlineButton}
          >
            <BookmarkIcon size={15} fill={isSaved ? "currentColor" : "none"} />
            <span className="max-sm:sr-only">{isSaved ? "Saved" : "Save"}</span>
          </button>
        )}
        <button type="button" onClick={share} disabled={!itineraryId} title={unavailable} className={outlineButton}>
          {shareState === "copied" ? <CheckIcon size={15} /> : <ShareIcon size={15} />}
          <span aria-live="polite" className="max-sm:sr-only">
            {shareState === "copied" ? "Link copied" : shareState === "failed" ? "Couldn't copy" : "Share"}
          </span>
        </button>
        <Link to="/" className="rounded-[10px] bg-ink px-4 py-2 text-sm font-semibold whitespace-nowrap text-white hover:bg-ink/85">
          New trip
        </Link>
        {save && <span aria-hidden="true" className="h-6 w-px bg-line max-sm:hidden" />}
        <AccountNav />
      </div>
    </header>
  );
}
