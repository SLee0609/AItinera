import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import AccountNav from "../components/AccountNav";
import Dialog from "../components/Dialog";
import DaysStepper from "../components/DaysStepper";
import Logo from "../components/Logo";
import { ArrowRightIcon, PinIcon } from "../components/icons";
import { pluralDays } from "../lib/format";
import { tripSearch } from "../lib/itinerary";

const EXAMPLE_TRIPS = [
  { city: "Tokyo", days: 4 },
  { city: "Rome", days: 3 },
  { city: "New York", days: 5 },
  { city: "Lisbon", days: 2 },
];

const STEPS = [
  {
    title: "Find attractions",
    body: "An AI model suggests attractions for your city.",
  },
  {
    title: "Verify each attraction",
    body: "Every suggestion is matched to a real Google Maps listing.",
  },
  {
    title: "Group attractions into days",
    body: "Attractions are grouped into days by how close they are to each other, while balancing the amount of sightseeing across days.",
  },
  {
    title: "Optimize routes",
    body: "Order each day's stops to minimize travel time.",
  },
];

const navLink = "rounded-lg px-1 py-1 font-medium text-sub hover:text-ink";

export default function LandingPage() {
  const navigate = useNavigate();
  const [city, setCity] = useState("");
  const [days, setDays] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"how" | "examples" | null>(null);

  const go = (c: string, d: number) => navigate(tripSearch(c, d));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = city.trim();
    if (!trimmed) {
      setError("Enter a city to plan a trip.");
      return;
    }
    go(trimmed, days);
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas bg-[radial-gradient(900px_420px_at_50%_0%,#E6F6F3_0%,transparent_70%)]">
      <header className="flex h-16 items-center gap-5 px-4 sm:gap-7 sm:px-10">
        <Logo />
        <nav className="flex gap-6 text-sm">
          <button type="button" className={navLink} onClick={() => setDialog("how")}>
            How it works
          </button>
          {/* The same examples are under the search box, so phones skip this link to fit the header. */}
          <button type="button" className={`${navLink} max-sm:hidden`} onClick={() => setDialog("examples")}>
            Examples
          </button>
        </nav>
        <div className="ml-auto">
          <AccountNav variant="full" />
        </div>
      </header>

      {/* Centered in the space below the header; the extra bottom padding (the header's height) puts it
          at the center of the whole screen. */}
      <main className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-[minmax(0,1fr)] content-center justify-items-center gap-5 px-4 pt-12 pb-28 text-center sm:px-10">
        <h1 className="max-w-[860px] font-display text-4xl leading-[1.06] font-bold tracking-[-0.03em] text-balance sm:text-[58px]">
          Create <span className="text-accent">efficient</span> travel itineraries. <span className="font-semibold text-sub">Less backtracking, more exploring.</span>
        </h1>

        <form
          onSubmit={submit}
          noValidate
          className="mt-5 grid w-full max-w-[860px] items-center gap-2 rounded-2xl border border-line bg-white p-2 text-left shadow-[0_18px_40px_-20px_rgb(15_23_42/0.25)] md:grid-cols-[1.6fr_1fr_auto]"
        >
          <div className="grid gap-0.5 px-4 py-2">
            <label htmlFor="destination" className="text-xs font-semibold">
              Destination
            </label>
            <div className="flex items-center gap-2">
              <PinIcon size={18} className="shrink-0 text-sub" />
              <input
                id="destination"
                type="text"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setError(null);
                }}
                placeholder="Where to? Try Paris"
                autoComplete="off"
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "destination-error" : undefined}
                className="w-full bg-transparent py-0.5 text-[17px] outline-none placeholder:text-sub/70"
              />
            </div>
          </div>
          <div className="grid gap-0.5 border-line px-4 py-2 max-md:border-t md:border-l">
            <label htmlFor="days" className="text-xs font-semibold">
              Trip length
            </label>
            <DaysStepper id="days" value={days} onChange={setDays} />
          </div>
          <button
            type="submit"
            className="flex h-14 items-center justify-center gap-2 rounded-xl bg-accent px-6 text-[15px] font-semibold text-white hover:bg-accent-hover"
          >
            Generate itinerary <ArrowRightIcon size={18} />
          </button>
        </form>
        {error && (
          <p id="destination-error" role="alert" className="-mt-1 text-sm font-medium text-red-700">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-center gap-2 text-[13px] text-sub">
          Try:
          {EXAMPLE_TRIPS.map((t) => (
            <button
              key={t.city}
              type="button"
              onClick={() => go(t.city, t.days)}
              className="rounded-full border border-line bg-white px-3 py-1 text-ink hover:border-sub"
            >
              {t.city} · {pluralDays(t.days)}
            </button>
          ))}
        </div>
      </main>

      <footer className="pb-5 text-center text-xs text-sub">
        <Link to="/privacy" className="hover:text-ink">
          Privacy policy
        </Link>
      </footer>

      <Dialog open={dialog === "how"} onClose={() => setDialog(null)} title="How it works">
        <p className="-mt-2 text-sm text-sub">
          AItinera goes beyond AI-generated travel suggestions by leveraging real-world geographical data to organize attractions into
          efficient daily routes.
        </p>
        <ol className="grid gap-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[28px_1fr] items-start gap-3">
              {/* Nudged down so the circle's top meets the top of the title text, not its line box. */}
              <span className="mt-1.5 grid size-7 place-items-center rounded-full bg-accent-soft text-[13px] font-bold text-accent">
                {i + 1}
              </span>
              <div>
                <h3 className="font-semibold">{s.title}</h3>
                <p className="text-sm text-sub">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Dialog>

      <Dialog open={dialog === "examples"} onClose={() => setDialog(null)} title="Example trips">
        <p className="-mt-2 text-sm text-sub">Pick one to generate an itinerary.</p>
        <ul className="grid gap-2">
          {EXAMPLE_TRIPS.map((t) => (
            <li key={t.city}>
              <button
                type="button"
                onClick={() => go(t.city, t.days)}
                className="flex w-full items-center justify-between rounded-xl border border-line px-4 py-3 text-left hover:border-accent"
              >
                <span className="font-semibold">{t.city}</span>
                <span className="flex items-center gap-2 text-sm text-sub">
                  {pluralDays(t.days)} <ArrowRightIcon size={16} />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Dialog>
    </div>
  );
}
