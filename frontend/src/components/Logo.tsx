import { Link } from "react-router";
import { RouteIcon } from "./icons";

export default function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2.5 font-display text-xl font-bold tracking-tight text-ink">
      <span className="grid size-7 place-items-center rounded-lg bg-accent text-white">
        <RouteIcon size={16} strokeWidth={2.2} />
      </span>
      {/* The teal "I" keeps the name from reading as "Altinera". */}
      <span>
        A<span className="text-accent">I</span>tinera
      </span>
    </Link>
  );
}
