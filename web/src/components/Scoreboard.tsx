import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import type { PlayerView, ScoreBreakdown } from "../types";
import { scoreTotal } from "../types";
import { LOCATION, seatColor } from "../theme";
import { Icon } from "./Icons";
import { Counter, HeliumIcon, SovereignIcon } from "./Tokens";

// Where the points came from, in the order the rulebook counts them.
const ROWS: {
  key: keyof ScoreBreakdown;
  label: string;
  icon: ReactNode;
  tint: string;
}[] = [
  { key: "core_values", label: "Core values", icon: "◆", tint: "#cfc3bd" },
  { key: "card_bonuses", label: "Card bonuses", icon: <Icon name="EndGame" size={13} />, tint: "#c9a4e8" },
  { key: "fleet", label: "Fleet Track", icon: <Icon name="Jupiter" size={13} />, tint: LOCATION.Jupiter.color },
  { key: "helium", label: "Helium ×3", icon: <HeliumIcon size={13} />, tint: LOCATION.Mars.color },
  { key: "sovereignty", label: "Sovereignty", icon: <SovereignIcon size={13} />, tint: LOCATION.Luna.color },
  { key: "influence", label: "Influence", icon: <Icon name="Institute" size={13} />, tint: LOCATION.Institute.color },
  { key: "excess_penalty", label: "Excess cards", icon: <Icon name="Banish" size={12} />, tint: "#c0605e" },
];

// The end of a game deserves the whole screen. It opens over the table and can
// be dismissed, because the first thing you want after seeing the number is to
// look at the board that produced it.
export function Scoreboard({ view }: { view: PlayerView }) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!view.scores) return null;
  const scores = view.scores;
  const seats = Object.keys(scores);
  const nameOf = (seat: string) =>
    seat === view.you.seat
      ? view.you.name
      : (view.opponents.find((o) => o.seat === seat)?.name ?? seat);
  const totals = Object.fromEntries(seats.map((s) => [s, scoreTotal(scores[s])]));
  const best = Math.max(...Object.values(totals));
  const winners = seats.filter((s) => totals[s] === best);
  const youWon = winners.includes(view.you.seat);

  if (!open) {
    return (
      <div className="shrink-0 border-t border-amber-400/40 bg-black/50 px-4 py-2 flex items-center gap-3 text-sm">
        <span className="font-display font-bold text-amber-200">
          {winners.map(nameOf).join(" & ")} took it, {best} to{" "}
          {Math.min(...Object.values(totals))}
        </span>
        <button
          onClick={() => setOpen(true)}
          className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[12px]"
        >
          Show the scores
        </button>
      </div>
    );
  }

  if (typeof document === "undefined") return null;
  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[88] grid place-items-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto thin-scroll"
      >
        <motion.div
          initial={{ scale: 0.94, y: 24 }}
          animate={{ scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 30 }}
          className="w-full max-w-2xl rounded-2xl p-6 sm:p-8 my-auto"
          style={{
            background: "linear-gradient(#1a1013, #0d0709)",
            boxShadow: "inset 0 0 0 1px rgba(232,188,85,.2), 0 30px 80px rgba(0,0,0,.7)",
          }}
        >
          <motion.p
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="text-center text-[10px] uppercase tracking-[0.4em] opacity-45"
          >
            {view.turn_number} turns
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 260, damping: 18 }}
            className="font-display text-center text-3xl sm:text-4xl font-black mb-1"
            style={{
              background: "linear-gradient(#ffe9b0, #e0a52c 55%, #9c6a15)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {winners.length > 1
              ? "A dead heat"
              : `${nameOf(winners[0])} ${youWon ? "rises" : "takes it"}`}
          </motion.h2>
          <p className="text-center text-xs opacity-45 mb-6">
            A strong table runs 200–300. Anything past 300 is a rout.
          </p>

          <div className="grid gap-3" style={{ gridTemplateColumns: `1fr repeat(${seats.length}, minmax(72px, auto))` }}>
            <span />
            {seats.map((s) => (
              <div key={s} className="text-right">
                <div className="flex items-center justify-end gap-1.5">
                  {totals[s] === best && <span title="Winner">👑</span>}
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: seatColor(s) }}
                  />
                  <span className="font-display font-bold text-sm truncate">{nameOf(s)}</span>
                </div>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.45 }}
                  className="font-display text-3xl font-black text-amber-200 tabular-nums leading-tight"
                >
                  <Counter value={totals[s]} />
                </motion.div>
              </div>
            ))}

            {ROWS.map(({ key, label, icon, tint }, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + i * 0.06 }}
                className="contents"
              >
                <span className="flex items-center gap-2 py-1.5 border-t border-white/6 text-[13px]">
                  <span className="grid place-items-center w-5 h-5 rounded" style={{ color: tint, background: `${tint}18` }}>
                    {icon}
                  </span>
                  <span className="opacity-75">{label}</span>
                </span>
                {seats.map((s) => {
                  const v = scores[s][key] as number;
                  const lead = v === Math.max(...seats.map((o) => scores[o][key] as number)) && v !== 0;
                  return (
                    <span
                      key={s}
                      className={`py-1.5 border-t border-white/6 text-right tabular-nums text-[13px] ${
                        v === 0 ? "opacity-30" : lead ? "text-amber-200 font-semibold" : "opacity-85"
                      }`}
                    >
                      {v < 0 ? `−${Math.abs(v)}` : v}
                    </span>
                  );
                })}
              </motion.div>
            ))}
          </div>

          {/* Where each player's points actually came from, at a glance. */}
          <div className="mt-6 space-y-2">
            {seats.map((s) => (
              <div key={s} className="flex items-center gap-2">
                <span
                  className="w-20 shrink-0 truncate text-[11px] uppercase tracking-wide"
                  style={{ color: seatColor(s) }}
                >
                  {nameOf(s)}
                </span>
                <span className="flex-1 flex h-2.5 rounded-full overflow-hidden bg-white/5">
                  {ROWS.filter(({ key }) => (scores[s][key] as number) > 0).map(({ key, tint }) => (
                    <motion.span
                      key={key}
                      initial={{ width: 0 }}
                      animate={{
                        width: `${((scores[s][key] as number) / Math.max(1, best)) * 100}%`,
                      }}
                      transition={{ delay: 0.8, duration: 0.7, ease: "easeOut" }}
                      style={{ background: tint }}
                      title={`${key}: ${scores[s][key]}`}
                    />
                  ))}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-7 flex justify-center gap-2">
            <button
              onClick={() => setOpen(false)}
              className="px-4 py-2 rounded-lg font-semibold text-black"
              style={{ background: "linear-gradient(#f0c85e, #c9962a)" }}
            >
              Look at the board
            </button>
            <a
              href="/"
              className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition text-sm self-center"
            >
              New game
            </a>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body,
  );
}
