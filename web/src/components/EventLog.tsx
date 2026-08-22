import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { describeEvent, type LogEvent } from "../eventText";
import { portrait } from "../theme";
import { Icon } from "./Icons";
import { useCardZoom } from "./CardZoom";

// The running narrative of the game. Doubles as the replay feed: for a finished
// game it holds the whole history. Lines that concern a card carry its portrait,
// which is both faster to scan than a name and a way back into the card itself.
export function EventLog({
  events,
  nameOf,
  youSeat,
  onScrub,
}: {
  events: LogEvent[];
  nameOf: (seat: string) => string;
  youSeat?: string;
  onScrub?: (seq: number) => void;
}) {
  const lines = events.map((e) => describeEvent(e, nameOf)).filter((l) => l !== null);
  const endRef = useRef<HTMLDivElement>(null);
  const { inspect } = useCardZoom();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lines.length]);

  return (
    <div className="flex flex-col h-full w-full min-w-0">
      <div className="px-3 py-2 text-[10px] uppercase tracking-[0.25em] opacity-40 border-b border-white/10 shrink-0">
        Game log
      </div>
      <div className="flex-1 overflow-y-auto thin-scroll px-2.5 py-2 space-y-0.5 text-[13px]">
        <AnimatePresence initial={false}>
          {lines.map((l) =>
            l.kind === "divider" ? (
              <motion.div
                key={l.seq}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 mb-1.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-300/85"
              >
                {l.icon && <Icon name={l.icon} size={11} />}
                <span className="shrink-0">{l.text}</span>
                <span className="flex-1 border-t border-amber-300/20" />
              </motion.div>
            ) : (
              <motion.div
                key={l.seq}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
                className={`flex items-center gap-1.5 leading-snug rounded px-1 py-0.5 ${
                  onScrub ? "cursor-pointer hover:bg-white/5" : ""
                }`}
                onClick={onScrub ? () => onScrub(l.seq) : undefined}
              >
                <span className="w-4 shrink-0 grid place-items-center opacity-70 text-amber-200/80">
                  {l.icon ? <Icon name={l.icon} size={12} /> : <span className="opacity-50">·</span>}
                </span>
                {l.cardId && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      inspect(l.cardId!);
                    }}
                    className="shrink-0 rounded-[3px] overflow-hidden hover:ring-1 hover:ring-amber-300 transition"
                    title="Look at this card"
                  >
                    <img src={portrait(l.cardId)} alt="" className="w-4 h-4 object-cover block" />
                  </button>
                )}
                <span className="min-w-0">
                  {l.seat && (
                    <span
                      className={`font-semibold ${
                        l.seat === youSeat ? "text-amber-200" : "text-[#e0b9c4]"
                      }`}
                    >
                      {nameOf(l.seat)}{" "}
                    </span>
                  )}
                  <span className="opacity-80">{l.text}</span>
                </span>
              </motion.div>
            ),
          )}
        </AnimatePresence>
        {lines.length === 0 && (
          <p className="opacity-30 text-xs px-1 py-4">Nothing has happened yet.</p>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
