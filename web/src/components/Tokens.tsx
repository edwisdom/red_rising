import { useEffect, useRef, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

// A number that rolls to its new value and flashes gold when it climbs — the
// digital stand-in for a token actually sliding across the board.
export function Counter({ value, className }: { value: number; className?: string }) {
  const spring = useSpring(value, { stiffness: 240, damping: 26 });
  const text = useTransform(spring, (v) => Math.round(v).toString());
  const prev = useRef(value);
  const [bump, setBump] = useState(false);

  useEffect(() => {
    spring.set(value);
    if (value !== prev.current) {
      setBump(true);
      const t = setTimeout(() => setBump(false), 550);
      prev.current = value;
      return () => clearTimeout(t);
    }
  }, [value, spring]);

  return (
    <motion.span
      className={`tabular-nums ${className ?? ""}`}
      animate={bump ? { scale: [1, 1.45, 1], color: ["#f2e9e4", "#ffd76a", "#f2e9e4"] } : {}}
      transition={{ duration: 0.5 }}
    >
      <motion.span>{text}</motion.span>
    </motion.span>
  );
}

/** A resource readout: icon, count, and a tooltip saying what it is worth. */
export function Pip({
  icon,
  tint,
  value,
  title,
  suffix,
}: {
  icon: React.ReactNode;
  tint: string;
  value: number;
  title: string;
  suffix?: string;
}) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 leading-none"
      style={{ background: `${tint}18`, boxShadow: `inset 0 0 0 1px ${tint}33` }}
    >
      <span style={{ color: tint, display: "grid", placeItems: "center" }}>{icon}</span>
      <Counter value={value} className="font-semibold text-[13px]" />
      {suffix && <span className="text-[10px] opacity-50">{suffix}</span>}
    </span>
  );
}

// Helium is a cut crystal in the box; a faceted gem reads better than a generic
// diamond glyph.
export function HeliumIcon({ size = 13 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d="M6 2h12l4 6-10 14L2 8l4-6zm.9 2L4.4 7.5h4.2L9.9 4H6.9zm5.1 0-1.3 3.5h3.6L13 4h-1zm4.1 0 1.3 3.5h4.2L19.1 4h-3zM4.9 9.5 11 18.2 8.1 9.5H4.9zm5.3 0L12 15l1.8-5.5h-3.6zm5.6 0-2.9 8.7 6.1-8.7h-3.2z" />
    </svg>
  );
}

export function SovereignIcon({ size = 13 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d="M3 7l4.2 3.2L12 3l4.8 7.2L21 7l-1.6 11.5H4.6L3 7zm3.4 13.5h11.2V22H6.4v-1.5z" />
    </svg>
  );
}
