import { useEffect, useRef, type ReactNode } from "react";
import { XIcon } from "./icons";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export default function Dialog({ open, onClose, title, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      // Clicking the backdrop (the dialog element itself, outside the panel) closes it.
      onClick={(e) => e.target === ref.current && onClose()}
      aria-labelledby="dialog-title"
      className="m-auto w-[min(540px,calc(100vw-32px))] rounded-2xl border border-line bg-white p-0 text-ink shadow-2xl backdrop:bg-ink/30"
    >
      <div className="grid gap-4 p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 id="dialog-title" className="font-display text-xl font-bold tracking-tight">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid size-8 place-items-center rounded-full text-sub hover:bg-track hover:text-ink"
          >
            <XIcon size={18} />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
