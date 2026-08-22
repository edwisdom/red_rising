import { useLayoutEffect, useRef, useState } from "react";
import { CARD_RATIO, stripEm } from "./components/CardView";

// A card's em scale is its width / 14 (see CardView), so a strip of N em costs
// N/14 of the card's width in height.
const EM_PER_WIDTH = 1 / 14;

interface Fit {
  /** How many cards sit side by side. */
  lanes: number;
  /** How many rows of lanes; each row gets its own share of the height. */
  rows?: number;
  /** Deepest stack in any lane; each card under the top one costs a strip. */
  stack?: number;
  /** Horizontal gap between lanes, px. */
  gap?: number;
  /** Vertical space the lane's own furniture takes (labels, padding), px. */
  chrome?: number;
  /** Horizontal padding inside each lane, px. */
  lanePad?: number;
  min?: number;
  max?: number;
}

/**
 * Size a row of cards to the box it actually occupies, so the table fills a
 * desktop window and still shows everything on a phone. Returns a ref for the
 * container to measure and the width to render each card at.
 */
export function useFitCards({
  lanes,
  rows = 1,
  stack = 1,
  gap = 12,
  chrome = 0,
  lanePad = 0,
  min = 96,
  max = 205,
}: Fit) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(min);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const { width, height } = el.getBoundingClientRect();
      if (!width || !height) return;
      const stackFactor =
        CARD_RATIO + stripEm(stack) * EM_PER_WIDTH * Math.max(0, stack - 1);
      const byHeight = (height / Math.max(1, rows) - chrome) / stackFactor;
      const n = Math.max(1, lanes);
      const byWidth = (width - gap * (n - 1) - lanePad * n) / n;
      setW(Math.round(Math.max(min, Math.min(max, byHeight, byWidth))));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [lanes, rows, stack, gap, chrome, lanePad, min, max]);

  return { ref, cardWidth: w };
}
