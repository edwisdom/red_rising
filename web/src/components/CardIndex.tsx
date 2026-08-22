import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { allCards } from "../cards";
import { CASTE, casteGradient, caste } from "../theme";
import { CardFull } from "./CardZoom";

// The whole 112-card deck, browsable. Mid-game you mostly want "what does that
// Gold do again?" — so this filters by caste and searches names *and* ability
// text, and shows the picked card full-size next to the grid.
export function CardIndex({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState("");
  const [color, setColor] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);

  const cards = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return allCards()
      .filter((c) => !color || c.color === color)
      .filter((c) => {
        if (!needle) return true;
        const hay = [
          c.name,
          c.color,
          c.deploy?.text ?? "",
          c.block?.text ?? "",
          c.endgame?.text ?? "",
          ...c.bonuses.map((b) => b.condition),
        ]
          .join(" ")
          .toLowerCase();
        return hay.includes(needle);
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [q, color]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && (picked ? setPicked(null) : onClose());
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, picked]);

  if (typeof document === "undefined") return null;
  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[85] bg-black/75 backdrop-blur-sm p-3 sm:p-6"
          onClick={onClose}
        >
          <motion.div
            initial={{ y: 24, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: 16, opacity: 0 }}
            transition={{ type: "spring", stiffness: 380, damping: 34 }}
            onClick={(e) => e.stopPropagation()}
            className="mx-auto max-w-6xl h-full flex flex-col rounded-2xl border border-white/10 bg-[#120c0e]/95 overflow-hidden"
          >
            <header className="flex items-center gap-3 px-4 py-3 border-b border-white/10 shrink-0">
              <h2 className="font-display font-bold tracking-wider text-amber-200">CARDS</h2>
              <input
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search names and abilities…"
                className="flex-1 min-w-0 px-3 py-1.5 rounded-lg bg-black/50 border border-white/10 text-sm outline-none focus:border-amber-400/60"
              />
              <span className="text-xs opacity-45 tabular-nums hidden sm:block">
                {cards.length}/112
              </span>
              <button
                onClick={onClose}
                className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-sm"
              >
                Esc
              </button>
            </header>

            <div className="flex gap-1.5 px-4 py-2 overflow-x-auto thin-scroll shrink-0">
              <Chip active={!color} onClick={() => setColor(null)} label="All" />
              {Object.keys(CASTE).map((k) => (
                <Chip
                  key={k}
                  active={color === k}
                  onClick={() => setColor(color === k ? null : k)}
                  label={k}
                  swatch={k}
                />
              ))}
            </div>

            <div className="flex-1 min-h-0 flex gap-4 px-4 pb-4">
              <div className="flex-1 min-w-0 overflow-y-auto thin-scroll">
                <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(150px,1fr))]">
                  {cards.map((c) => {
                    const cc = caste(c.color);
                    const on = picked === c.id;
                    return (
                      <button
                        key={c.id}
                        onClick={() => setPicked(c.id)}
                        className="text-left rounded-lg overflow-hidden transition hover:-translate-y-0.5"
                        style={{
                          background: "rgba(255,255,255,.03)",
                          boxShadow: on
                            ? `0 0 0 2px var(--gild)`
                            : `inset 0 0 0 1px ${cc.base}33`,
                        }}
                      >
                        <div className="flex items-center gap-2 p-1.5">
                          <img
                            src={`/characters/${c.id}.webp`}
                            alt=""
                            loading="lazy"
                            className="w-11 h-11 rounded object-cover shrink-0"
                          />
                          <span className="min-w-0">
                            <span className="block truncate font-semibold text-[13px] leading-tight">
                              {c.name}
                            </span>
                            <span className="block text-[10px] uppercase tracking-wider opacity-55">
                              {c.color} · {c.core_value}
                            </span>
                          </span>
                        </div>
                        <div
                          style={{ height: 3, background: casteGradient(c.color) }}
                          aria-hidden="true"
                        />
                      </button>
                    );
                  })}
                  {cards.length === 0 && (
                    <p className="opacity-45 text-sm col-span-full py-8 text-center">
                      Nothing matches “{q}”.
                    </p>
                  )}
                </div>
              </div>

              <aside className="hidden lg:block w-[320px] shrink-0 overflow-y-auto thin-scroll">
                {picked ? (
                  <CardFull cardId={picked} width={310} onCardRef={setPicked} />
                ) : (
                  <div className="h-full grid place-items-center text-center text-sm opacity-35 px-6">
                    Pick a card to read it in full.
                  </div>
                )}
              </aside>
            </div>
          </motion.div>

          {/* On narrow screens the picked card takes over instead of sitting beside. */}
          <AnimatePresence>
            {picked && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="lg:hidden fixed inset-0 z-[86] grid place-items-center bg-black/80 p-4"
                onClick={() => setPicked(null)}
              >
                <div onClick={(e) => e.stopPropagation()}>
                  <CardFull cardId={picked} width={300} onCardRef={setPicked} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

function Chip({
  active,
  onClick,
  label,
  swatch,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  swatch?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide transition ${
        active ? "bg-amber-400 text-black" : "bg-white/6 hover:bg-white/12 opacity-80"
      }`}
    >
      {swatch && (
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ background: casteGradient(swatch), boxShadow: "0 0 0 1px rgba(0,0,0,.4)" }}
        />
      )}
      {label}
    </button>
  );
}
