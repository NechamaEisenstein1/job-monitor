import { useEffect, useState } from "react";

/** A text field that commits its value only after typing pauses, so typing does not fire a
 *  request per keystroke. Follows `value` when it changes from outside (e.g. "clear all"). */
export function useDebouncedField(value: string, onCommit: (next: string) => void, delayMs = 300) {
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  useEffect(() => {
    if (draft === value) return;
    const timer = setTimeout(() => onCommit(draft), delayMs);
    return () => clearTimeout(timer);
  }, [draft]); // eslint-disable-line react-hooks/exhaustive-deps

  return [draft, setDraft] as const;
}
