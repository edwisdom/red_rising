import { AnimatePresence, motion } from "framer-motion";
import type { LocationView } from "../types";
import { CardView } from "./CardView";

const BONUS: Record<string, string> = {
  Jupiter: "🚀 Advance Fleet",
  Mars: "💎 Gain Helium",
  Luna: "👑 Sovereign",
  Institute: "🏛️ Influence",
};
const DISPLAY: Record<string, string> = { Institute: "The Institute" };

// A location renders its stack as an overlap: covered cards peek out at the top,
// the top card is shown in full. Clicking is enabled only when this location is a
// legal choice for the current decision.
export function LocationPile({
  loc,
  selectable,
  onSelect,
}: {
  loc: LocationView;
  selectable: boolean;
  onSelect?: () => void;
}) {
  const covered = loc.cards.slice(0, -1);
  const top = loc.cards[loc.cards.length - 1];

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`text-xs font-semibold uppercase tracking-wide ${
          selectable ? "text-amber-300" : "opacity-70"
        }`}
      >
        {DISPLAY[loc.location] ?? loc.location}
      </div>
      <div className="text-[10px] opacity-50 -mt-1">{BONUS[loc.location]}</div>
      <div
        className={`flex flex-col items-center rounded-lg p-1 ${
          selectable ? "ring-2 ring-amber-400 cursor-pointer" : "ring-1 ring-white/5"
        }`}
        onClick={selectable ? onSelect : undefined}
        style={{ minHeight: 180, minWidth: 130, justifyContent: loc.cards.length ? "start" : "center" }}
      >
        {loc.cards.length === 0 && <span className="opacity-30 text-xs">empty</span>}
        <div className="relative flex flex-col" style={{ gap: 0 }}>
          {covered.map((c, i) => (
            <CardView key={i} cardId={c.card_id} faceDown={c.face_down} size="md" covered />
          ))}
          <AnimatePresence mode="popLayout" initial={false}>
            {top && (
              <motion.div
                key={top.card_id ?? "facedown"}
                initial={{ opacity: 0, y: -12, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.18 }}
              >
                <CardView cardId={top.card_id} faceDown={top.face_down} size="md" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
