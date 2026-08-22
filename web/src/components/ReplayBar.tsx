import { useEffect, useState } from "react";
import { motion } from "framer-motion";

// Scrubber for stepping through a finished (or in-progress) game. `step` counts
// answers applied; 0 is the opening position, `total` is now. Play walks it
// forward on its own, which is how you actually want to review a game — watching
// it, not clicking through it.
const TICK_MS = 700;

export function ReplayBar({
  step,
  total,
  onSeek,
  onExit,
}: {
  step: number;
  total: number;
  onSeek: (step: number) => void;
  onExit: () => void;
}) {
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    if (step >= total) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => onSeek(step + 1), TICK_MS);
    return () => clearTimeout(t);
  }, [playing, step, total, onSeek]);

  return (
    <div
      className="shrink-0 flex items-center gap-2 px-3 sm:px-4 py-2 text-sm border-b border-amber-400/40"
      style={{ background: "linear-gradient(rgba(232,188,85,.14), rgba(232,188,85,.05))" }}
    >
      <span className="font-display text-[11px] font-bold uppercase tracking-[0.2em] text-amber-200 shrink-0">
        Replay
      </span>
      <Btn onClick={() => (setPlaying(false), onSeek(Math.max(0, step - 1)))} label="Step back">
        ◀
      </Btn>
      <Btn
        onClick={() => (step >= total ? (onSeek(0), setPlaying(true)) : setPlaying((p) => !p))}
        label={playing ? "Pause" : "Play"}
        accent
      >
        {playing ? "❚❚" : step >= total ? "↻" : "▶"}
      </Btn>
      <Btn
        onClick={() => (setPlaying(false), onSeek(Math.min(total, step + 1)))}
        label="Step forward"
      >
        ▶
      </Btn>
      <div className="flex-1 relative h-5 flex items-center min-w-0">
        <span className="absolute inset-x-0 h-1 rounded-full bg-white/10" />
        <motion.span
          className="absolute left-0 h-1 rounded-full bg-amber-400"
          animate={{ width: `${total ? (step / total) * 100 : 0}%` }}
          transition={{ duration: 0.2 }}
        />
        <input
          type="range"
          min={0}
          max={total}
          value={step}
          onChange={(e) => (setPlaying(false), onSeek(Number(e.target.value)))}
          className="relative w-full accent-amber-400 opacity-0 cursor-pointer h-5"
          aria-label="Replay position"
        />
        <motion.span
          className="absolute w-3 h-3 rounded-full bg-amber-300 pointer-events-none"
          style={{ boxShadow: "0 0 8px rgba(232,188,85,.8)" }}
          animate={{ left: `calc(${total ? (step / total) * 100 : 0}% - 6px)` }}
          transition={{ duration: 0.2 }}
        />
      </div>
      <span className="tabular-nums opacity-60 text-xs shrink-0">
        {step} / {total}
      </span>
      <button
        onClick={onExit}
        className="shrink-0 px-3 py-1 rounded-lg font-semibold text-black text-[12px]"
        style={{ background: "linear-gradient(#f0c85e, #c9962a)" }}
      >
        Back to now
      </button>
    </div>
  );
}

function Btn({
  onClick,
  label,
  children,
  accent,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`shrink-0 w-7 h-7 grid place-items-center rounded-lg text-[11px] transition ${
        accent ? "bg-amber-400/25 hover:bg-amber-400/40 text-amber-100" : "bg-white/8 hover:bg-white/18"
      }`}
    >
      {children}
    </button>
  );
}
