import { useEffect } from "react";
import { Link } from "react-router";
import { CheckIcon } from "./icons";

export interface ToastMessage {
  text: string;
  tone: "success" | "error";
  link?: { to: string; label: string };
}

/** A short message at the bottom of the screen that hides itself after a few seconds. */
export default function Toast({ message, onDone }: { message: ToastMessage | null; onDone: () => void }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDone, 4000);
    return () => clearTimeout(t);
  }, [message, onDone]);

  return (
    <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-8 z-40 flex justify-center px-4">
      {message && (
        <div className="pointer-events-auto flex items-center gap-3.5 rounded-xl bg-ink py-3 pr-3.5 pl-4 text-sm text-white shadow-[0_18px_40px_-12px_rgb(15_23_42/0.4)]">
          {message.tone === "success" && <CheckIcon size={16} strokeWidth={2.4} className="shrink-0 text-teal-300" />}
          <span>{message.text}</span>
          {message.link && (
            <Link to={message.link.to} className="font-semibold whitespace-nowrap text-teal-300 hover:text-teal-200">
              {message.link.label}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
