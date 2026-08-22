import { useEffect, useRef, useState } from "react";

/**
 * True for `ms` after `value` changes. Lets a component celebrate a change
 * (a glow, a pop) without the caller threading "what was it before" through
 * props, and without re-firing on unrelated re-renders.
 */
export function useChanged<T>(value: T, ms = 700): boolean {
  const prev = useRef(value);
  const [hot, setHot] = useState(false);

  useEffect(() => {
    if (Object.is(prev.current, value)) return;
    prev.current = value;
    setHot(true);
    const t = setTimeout(() => setHot(false), ms);
    return () => clearTimeout(t);
  }, [value, ms]);

  return hot;
}
