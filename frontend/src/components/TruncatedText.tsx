import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/**
 * Single-line text that ends in an ellipsis when it doesn't fit. Hovering shows the full text in a
 * tooltip, but only when it is cut off. The tooltip is portaled to <body> so scrolling or
 * overflow-hidden ancestors don't clip it.
 */
export default function TruncatedText({ text, className = "" }: { text: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [anchor, setAnchor] = useState<DOMRect | null>(null);

  const show = () => {
    const el = ref.current;
    if (el && el.scrollWidth > el.clientWidth) setAnchor(el.getBoundingClientRect());
  };

  // The tooltip is positioned once on open, so close it if the text moves underneath it.
  useEffect(() => {
    if (!anchor) return;
    const close = () => setAnchor(null);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [anchor]);

  const left = anchor ? Math.max(8, anchor.left - 8) : 0;
  const below = anchor !== null && anchor.top < 48;

  return (
    <>
      <span ref={ref} className={`truncate ${className}`} onMouseEnter={show} onMouseLeave={() => setAnchor(null)}>
        {text}
      </span>
      {anchor &&
        createPortal(
          // The full text is already in the DOM for assistive tech, so the tooltip is visual only.
          <div
            role="tooltip"
            aria-hidden="true"
            className="pointer-events-none fixed z-50 rounded-lg bg-ink px-2.5 py-1.5 text-[12.5px] leading-snug font-medium text-white shadow-[0_6px_20px_-6px_rgb(15_23_42/0.45)]"
            style={{
              left,
              top: below ? anchor.bottom + 6 : anchor.top - 6,
              transform: below ? undefined : "translateY(-100%)",
              maxWidth: `min(320px, calc(100vw - ${left + 8}px))`,
            }}
          >
            {text}
          </div>,
          document.body,
        )}
    </>
  );
}
