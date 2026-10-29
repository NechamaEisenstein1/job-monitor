import { useEffect, useState } from "react";

/** Whether a CSS media query matches, kept up to date as the window resizes. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = () => setMatches(list.matches);
    onChange();
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

/** Tailwind's `lg` breakpoint: wide enough for a list and a side panel. */
export const WIDE_SCREEN = "(min-width: 1024px)";
