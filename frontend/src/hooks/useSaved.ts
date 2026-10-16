import { useCallback, useEffect, useRef, useState } from "react";
import { getSavedStatus, saveItinerary, unsaveItinerary } from "../api/client";
import { useAuth } from "../auth/context";

/** Whether the signed-in user has saved itinerary `id`, and a way to change it. */
export function useSaved(id: string | undefined) {
  const { user } = useAuth();
  const userId = user?.id;
  // null while unknown (guest, no ID, or still checking).
  const [saved, setSaved] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  // Bumped by every change, so a status check that started earlier can't overwrite it.
  const version = useRef(0);

  useEffect(() => {
    setSaved(null);
    if (!id || !userId) return;
    const controller = new AbortController();
    const started = version.current;
    getSavedStatus(id, controller.signal)
      .then((s) => version.current === started && setSaved(s.saved))
      .catch(() => {
        // Leave it unknown; clicking Save still works.
        if (!controller.signal.aborted && version.current === started) setSaved(false);
      });
    return () => controller.abort();
  }, [id, userId]);

  /** Saves or unsaves. Resolves to an error message, or null on success. */
  const setTo = useCallback(
    async (next: boolean): Promise<string | null> => {
      if (!id) return "This trip can't be saved.";
      version.current += 1;
      setBusy(true);
      try {
        const status = await (next ? saveItinerary(id) : unsaveItinerary(id));
        setSaved(status.saved);
        return null;
      } catch (err) {
        return err instanceof Error ? err.message : "Something went wrong. Try again.";
      } finally {
        setBusy(false);
      }
    },
    [id],
  );

  return { saved, busy, setTo };
}
