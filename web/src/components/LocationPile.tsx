import { AnimatePresence, motion } from "framer-motion";
import type { LocationView } from "../types";
import { LOCATION, LOCATION_LABEL } from "../theme";
import { CardView, stripEm } from "./CardView";
import { Icon, LOCATION_ICON } from "./Icons";
import { Zoomable } from "./CardZoom";

// A location is a lit plinth with a stack of cards on it. Covered cards show only
// their top band, exactly like the physical overlap, and the top card is dealt in
// so you can see what just landed.
/** Fixed vertical budget for a location's label block (see useFitCards.chrome). */
export const HEADER_H = 58;

export function LocationPile({
  loc,
  selectable,
  onSelect,
  width,
}: {
  loc: LocationView;
  selectable: boolean;
  onSelect?: () => void;
  /** Card width in px — the board sizes its piles to the room it actually has. */
  width: number;
}) {
  const covered = loc.cards.slice(0, -1);
  const top = loc.cards[loc.cards.length - 1];
  const meta = LOCATION[loc.location] ?? { color: "#888", glow: "#888", bonus: "" };
  const w = width;
  // Below this the label furniture costs more than it tells you.
  const roomy = w >= 118;
  const band = stripEm(loc.cards.length);
  const ids = loc.cards.map((c) => c.card_id).filter((x): x is string => !!x);

  return (
    <div className="flex flex-col items-center gap-1.5" style={{ width: w + 16 }}>
      {/* The header keeps a fixed budget so the board can size its cards without
          the label height chasing the card height. The bonus line is the first
          thing to go when the pile gets small. */}
      <div
        className="flex flex-col items-center justify-end gap-0.5 text-center leading-none"
        style={{ height: HEADER_H }}
      >
        <span
          className="grid place-items-center rounded-full shrink-0"
          style={{
            width: roomy ? 32 : 24,
            height: roomy ? 32 : 24,
            color: meta.color,
            background: `radial-gradient(circle, ${meta.color}33, transparent 72%)`,
            filter: `drop-shadow(0 0 7px ${meta.glow}88)`,
          }}
        >
          <Icon name={LOCATION_ICON[loc.location] ?? "Deck"} size={roomy ? 23 : 17} />
        </span>
        <span
          className={`font-display font-bold uppercase leading-none ${
            selectable ? "text-amber-200" : ""
          }`}
          style={{
            fontSize: roomy ? 11 : 9.5,
            color: selectable ? undefined : meta.color,
          }}
        >
          {LOCATION_LABEL[loc.location] ?? loc.location}
        </span>
        {roomy && (
          <span className="text-[9.5px] uppercase tracking-wide opacity-45 leading-tight">
            {meta.bonus}
          </span>
        )}
      </div>

      <motion.div
        onClick={selectable ? onSelect : undefined}
        animate={selectable ? { scale: 1 } : { scale: 1 }}
        whileHover={selectable ? { scale: 1.03 } : undefined}
        className={`relative w-full rounded-xl p-2 transition-colors ${
          selectable ? "cursor-pointer" : ""
        }`}
        style={{
          minHeight: w * 1.4 + 22,
          // The plinth: a soft pool of the location's own light on the felt.
          background: `radial-gradient(120% 70% at 50% 0%, ${meta.color}1f, transparent 70%), rgba(0,0,0,.28)`,
          boxShadow: selectable
            ? `inset 0 0 0 2px var(--gild), 0 0 22px rgba(232,188,85,.35)`
            : `inset 0 0 0 1px ${meta.color}2e`,
        }}
      >
        {loc.cards.length === 0 && (
          <div
            className="absolute inset-2 rounded-lg border border-dashed grid place-items-center text-[10px] uppercase tracking-widest"
            style={{ borderColor: `${meta.color}40`, color: `${meta.color}70` }}
          >
            empty
          </div>
        )}

        <div className="relative flex flex-col items-center">
          {covered.map((c, i) => (
            <Zoomable key={`${c.card_id ?? "fd"}-${i}`} cardId={c.face_down ? null : c.card_id} list={ids}>
              <CardView cardId={c.card_id} faceDown={c.face_down} width={w} strip stripHeight={band} />
            </Zoomable>
          ))}
          <AnimatePresence mode="popLayout" initial={false}>
            {top && (
              <motion.div
                key={`${top.card_id ?? "facedown"}-${loc.cards.length}`}
                initial={{ opacity: 0, y: -26, rotate: -4, scale: 0.92 }}
                animate={{ opacity: 1, y: 0, rotate: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: "spring", stiffness: 420, damping: 28 }}
              >
                <Zoomable cardId={top.face_down ? null : top.card_id} list={ids}>
                  <CardView cardId={top.card_id} faceDown={top.face_down} width={w} />
                </Zoomable>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {loc.cards.length > 1 && (
          <div className="absolute -top-1.5 -right-1.5 px-1.5 rounded-full bg-black/80 border border-white/15 text-[10px] tabular-nums opacity-80">
            {loc.cards.length}
          </div>
        )}
      </motion.div>
    </div>
  );
}
