import { motion } from "framer-motion";
import type { Option, PendingDecision, WaitingOn } from "../types";
import { getCard } from "../cards";
import { caste, LOCATION, LOCATION_LABEL, portrait } from "../theme";
import { Icon, LOCATION_ICON } from "./Icons";

// Every decision in the game is answerable from here, whatever else the board
// offers. Options that name a card or a location get shown as that thing —
// a portrait, or the location's own icon and colour — rather than as its id.
export function DecisionBar({
  pending,
  waiting,
  onAnswer,
}: {
  pending: PendingDecision | null;
  waiting: WaitingOn | null;
  onAnswer: (tokens: string[]) => void;
}) {
  // Deliberately not an AnimatePresence swap: `mode="wait"` holds the outgoing
  // prompt on screen until its exit finishes, and a stalled exit means the next
  // decision never mounts — the board lights up but the bar still asks the last
  // question. Keying the inner block on the decision id replays the entrance
  // without ever gating the new prompt on the old one leaving.
  if (pending) {
    return (
      <div
        className="shrink-0 border-t border-amber-400/45 bg-gradient-to-t from-[#1a0d10] to-[#12080b]/95 backdrop-blur px-3 sm:px-4 py-2.5"
        style={{ boxShadow: "0 -10px 30px rgba(0,0,0,.5), inset 0 1px 0 rgba(232,188,85,.35)" }}
      >
        <motion.div
          key={pending.id}
          initial={{ y: 8, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        >
          <div className="flex items-baseline gap-2 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-300 pulse-ring shrink-0" />
            <span className="font-display text-[13px] font-bold tracking-wide text-amber-200">
              {pending.prompt}
            </span>
            {pending.max_choices > 1 && (
              <span className="text-[11px] opacity-50">
                choose {pending.min_choices}–{pending.max_choices}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {pending.options.map((o, i) => (
              <OptionButton key={o.token} o={o} i={i} onClick={() => onAnswer([o.token])} />
            ))}
          </div>
        </motion.div>
      </div>
    );
  }

  if (waiting) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="shrink-0 border-t border-white/10 bg-black/50 backdrop-blur px-4 py-2.5 flex items-center gap-2 text-sm"
      >
        <span className="flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((n) => (
            <motion.span
              key={n}
              className="w-1.5 h-1.5 rounded-full bg-white/50"
              animate={{ opacity: [0.25, 1, 0.25] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: n * 0.18 }}
            />
          ))}
        </span>
        <span className="opacity-70">
          Waiting for <span className="font-semibold text-amber-200/90">{waiting.name}</span>
        </span>
        <span className="opacity-40 text-xs truncate">{waiting.prompt}</span>
      </motion.div>
    );
  }

  return null;
}

function OptionButton({ o, i, onClick }: { o: Option; i: number; onClick: () => void }) {
  const card = o.card_id ? getCard(o.card_id) : undefined;
  const locMeta = o.location ? LOCATION[o.location] : undefined;
  const tint = card ? caste(card.color).base : (locMeta?.color ?? "#e8bc55");

  const inner = card ? (
    <>
      <img
        src={portrait(card.id)}
        alt=""
        className="w-5 h-5 rounded object-cover shrink-0"
        loading="lazy"
      />
      <span className="font-semibold">{card.name}</span>
      <span className="text-[11px] opacity-55 tabular-nums">{card.core_value}</span>
    </>
  ) : o.location ? (
    <>
      <Icon name={LOCATION_ICON[o.location] ?? "Deck"} size={15} style={{ color: tint }} />
      <span className="font-semibold">{LOCATION_LABEL[o.location] ?? o.location}</span>
    </>
  ) : (
    <span className="font-semibold capitalize">{o.label}</span>
  );

  return (
    <motion.button
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(i * 0.025, 0.3) }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] leading-none transition-colors"
      style={{
        background: `linear-gradient(${tint}22, ${tint}11)`,
        boxShadow: `inset 0 0 0 1px ${tint}66`,
        color: "#f4ece7",
      }}
    >
      {inner}
    </motion.button>
  );
}
