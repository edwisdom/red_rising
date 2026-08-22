import { motion } from "framer-motion";
import type { OpponentView, SelfView } from "../types";
import { LOCATION } from "../theme";
import { seatColor } from "../theme";
import { Counter, HeliumIcon, Pip, SovereignIcon } from "./Tokens";

// One player's side of the table: who they are, what they hold privately, and —
// when it is their turn — a lit rim so you never have to hunt for whose move it
// is. The Fleet Track and Institute influence are deliberately NOT here: they are
// shared board spaces, and reading them off two separate corners of the screen
// made the one comparison that matters into a memory test. They live in
// BoardTracks now.
export function PlayerPanel({
  p,
  isSelf,
  isCurrent,
  handCount,
  compact,
}: {
  p: SelfView | OpponentView;
  isSelf: boolean;
  isCurrent: boolean;
  handCount: number;
  compact?: boolean;
}) {
  return (
    <motion.div
      layout
      animate={{
        boxShadow: isCurrent
          ? "inset 0 0 0 1.5px rgba(232,188,85,.85), 0 0 26px rgba(232,188,85,.22)"
          : "inset 0 0 0 1px rgba(255,255,255,.09)",
      }}
      transition={{ duration: 0.35 }}
      className="rounded-xl px-3 py-2 bg-black/35 backdrop-blur-sm"
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${isCurrent ? "pulse-ring" : ""}`}
          style={{ background: seatColor(p.seat), opacity: isCurrent ? 1 : 0.55 }}
          title={isCurrent ? "Their turn" : p.name}
        />
        <span className="font-display font-bold text-[15px] leading-none">{p.name}</span>
        <span className="text-[10px] uppercase tracking-[0.14em] opacity-45">House {p.house}</span>
        {isSelf && <span className="text-[10px] uppercase tracking-wider text-amber-300/70">you</span>}
        {p.has_sovereign && (
          <motion.span
            initial={{ scale: 0, rotate: -30 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 14 }}
            className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{
              color: "#3a2a05",
              background: `radial-gradient(circle at 30% 25%, ${LOCATION.Luna.color}, #b57f0d)`,
              boxShadow: "0 0 12px rgba(255,182,26,.45)",
            }}
            title="Holds the Sovereign token — 10 VP"
          >
            <SovereignIcon size={11} />
            Sovereign
          </motion.span>
        )}
      </div>

      <div className={`flex items-center gap-1.5 flex-wrap ${compact ? "mt-1" : "mt-1.5"}`}>
        <Pip
          icon={<HeliumIcon />}
          tint={LOCATION.Mars.color}
          value={p.helium}
          title={`${p.helium} Helium — 3 VP each`}
          suffix="He"
        />
        <span
          className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 leading-none bg-white/5"
          title={`${handCount} cards in hand`}
        >
          <span className="opacity-60 text-[12px]">🂠</span>
          <Counter value={handCount} className="font-semibold text-[13px]" />
        </span>
      </div>
    </motion.div>
  );
}
