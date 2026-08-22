import { useEffect, useState } from "react";

/** Subscribe to a media query, SSR-safe and without a resize listener. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

/** Wide enough to park the game log beside the board without squeezing it. */
export const WIDE = "(min-width: 1100px)";
