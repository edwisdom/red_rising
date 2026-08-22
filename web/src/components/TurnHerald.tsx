import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

// Two people playing over a link spend most of the game waiting on each other,
// often in a background tab. When the turn actually comes back to you the board
// should say so — once, loudly, and then get out of the way. The tab title
// carries the same news for when the window is not in front.
export function TurnHerald({
  yourTurn,
  yourName,
  waitingOn,
  finished,
}: {
  yourTurn: boolean;
  yourName: string;
  waitingOn: string | null;
  finished: boolean;
}) {
  const [herald, setHerald] = useState(false);
  const wasYours = useRef(yourTurn);

  useEffect(() => {
    if (yourTurn && !wasYours.current && !finished) {
      setHerald(true);
      const t = setTimeout(() => setHerald(false), 1500);
      wasYours.current = yourTurn;
      return () => clearTimeout(t);
    }
    wasYours.current = yourTurn;
  }, [yourTurn, finished]);

  useEffect(() => {
    document.title = finished
      ? "Game over — Red Rising"
      : yourTurn
        ? `● Your turn — Red Rising`
        : waitingOn
          ? `${waitingOn} to play — Red Rising`
          : "Red Rising";
    return () => {
      document.title = "Red Rising";
    };
  }, [yourTurn, waitingOn, finished]);

  return (
    <AnimatePresence>
      {herald && (
        <motion.div
          key="herald"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed inset-0 z-[70] grid place-items-center pointer-events-none"
        >
          {/* A gold wash sweeping the table, then the call. */}
          <motion.span
            className="absolute inset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.5, 0] }}
            transition={{ duration: 1.3, times: [0, 0.25, 1] }}
            style={{
              background:
                "radial-gradient(60% 40% at 50% 50%, rgba(232,188,85,.22), transparent 70%)",
            }}
          />
          <motion.div
            initial={{ scale: 0.8, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 1.06, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 18 }}
            className="text-center"
          >
            <div
              className="font-display text-4xl sm:text-6xl font-black tracking-[0.14em]"
              style={{
                background: "linear-gradient(#fff3d0, #e6b342 55%, #9c6a15)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                filter: "drop-shadow(0 6px 22px rgba(232,188,85,.35))",
              }}
            >
              YOUR TURN
            </div>
            <div className="mt-1 text-[10px] uppercase tracking-[0.4em] opacity-45">{yourName}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
