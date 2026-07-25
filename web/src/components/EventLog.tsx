import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { describeEvent, type LogEvent } from "../eventText";

// The running narrative of the game. Doubles as the replay feed: for a finished
// game it holds the whole history.
export function EventLog({
  events,
  nameOf,
  onScrub,
}: {
  events: LogEvent[];
  nameOf: (seat: string) => string;
  onScrub?: (seq: number) => void;
}) {
  const lines = events.map((e) => describeEvent(e, nameOf)).filter((l) => l !== null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lines.length]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs uppercase tracking-wide opacity-50 border-b border-white/10">
        Game log
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 text-sm">
        <AnimatePresence initial={false}>
          {lines.map((l) =>
            l.kind === "divider" ? (
              <motion.div
                key={l.seq}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 mb-1 flex items-center gap-2 text-xs uppercase tracking-wide text-amber-300/80"
              >
                <span>{l.icon}</span>
                <span>{l.text}</span>
                <span className="flex-1 border-t border-amber-300/20" />
              </motion.div>
            ) : (
              <motion.div
                key={l.seq}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex gap-2 leading-snug ${onScrub ? "cursor-pointer hover:bg-white/5 rounded px-1" : ""}`}
                onClick={onScrub ? () => onScrub(l.seq) : undefined}
              >
                <span className="opacity-70">{l.icon}</span>
                <span className="opacity-90">{l.text}</span>
              </motion.div>
            ),
          )}
        </AnimatePresence>
        <div ref={endRef} />
      </div>
    </div>
  );
}
