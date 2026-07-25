import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useGame, type Creds } from "../store";
import { GameSocket } from "../ws";
import { CardView } from "./CardView";
import { LocationPile } from "./LocationPile";
import { PlayerPanel } from "./PlayerPanel";
import { DecisionBar } from "./DecisionBar";
import { Scoreboard } from "./Scoreboard";
import { EventLog } from "./EventLog";
import { ReplayBar } from "./ReplayBar";

export function Game({ creds }: { creds: Creds }) {
  const live = useGame((s) => s.view);
  const liveEvents = useGame((s) => s.events);
  const replay = useGame((s) => s.replay);
  const setReplay = useGame((s) => s.setReplay);
  const status = useGame((s) => s.status);
  const error = useGame((s) => s.error);
  const sockRef = useRef<GameSocket | null>(null);
  const [showLog, setShowLog] = useState(true);

  useEffect(() => {
    const sock = new GameSocket(creds);
    sockRef.current = sock;
    sock.connect();
    return () => sock.close();
  }, [creds]);

  const view = replay ? replay.view : live;
  const events = replay ? replay.events : liveEvents;

  const answer = (tokens: string[]) => {
    if (!replay && live?.pending) sockRef.current?.answer(live.pending.id, tokens);
  };

  const nameOf = useMemo(() => {
    const names = new Map<string, string>();
    if (view) {
      names.set(view.you.seat, view.you.name);
      for (const o of view.opponents) names.set(o.seat, o.name);
    }
    return (seat: string) => names.get(seat) ?? seat;
  }, [view]);

  const seekReplay = async (step: number) => {
    const url = `/api/games/${creds.gameId}/replay?seat=${creds.seat}&token=${encodeURIComponent(creds.token)}&step=${step}`;
    const data = await (await fetch(url)).json();
    setReplay({ view: data.view, events: data.events, step: data.step, total: data.total });
  };

  // Map location/card options to answer tokens (unavailable in replay).
  const { locTokens, cardTokens } = useMemo(() => {
    const locTokens = new Map<string, string>();
    const cardTokens = new Map<string, string>();
    if (!replay) {
      for (const o of live?.pending?.options ?? []) {
        if (o.location) locTokens.set(o.location, o.token);
        if (o.card_id) cardTokens.set(o.card_id, o.token);
      }
    }
    return { locTokens, cardTokens };
  }, [live?.pending, replay]);

  if (error && !view) return <Centered>{error}</Centered>;
  if (!view) return <Centered>{status === "connecting" ? "Connecting…" : "…"}</Centered>;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <div className="font-bold tracking-wide">RED RISING</div>
        <div className="flex items-center gap-3 text-xs">
          <span className="opacity-60">
            Turn {view.turn_number} · deck {view.deck_count} · banished {view.banished.length}
          </span>
          <ConnDot status={status} />
          {!replay && liveEvents.length > 0 && (
            <button
              onClick={() => sockRef.current?.undo()}
              className="px-2 py-1 rounded bg-white/10 hover:bg-white/20"
              title="Undo the last action"
            >
              ↺ Undo
            </button>
          )}
          {!replay && (
            <button
              onClick={() => seekReplay(0)}
              className="px-2 py-1 rounded bg-white/10 hover:bg-white/20"
              title="Replay the game from the start"
            >
              ⏮ Replay
            </button>
          )}
          <button
            onClick={() => setShowLog((v) => !v)}
            className="px-2 py-1 rounded bg-white/10 hover:bg-white/20"
          >
            {showLog ? "Hide log" : "Show log"}
          </button>
        </div>
      </header>

      {replay && (
        <ReplayBar
          step={replay.step}
          total={replay.total}
          onSeek={seekReplay}
          onExit={() => setReplay(null)}
        />
      )}

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 flex flex-col min-w-0">
          {/* Opponents */}
          <div className="flex flex-wrap gap-2 px-4 py-3">
            {view.opponents.map((o) => (
              <PlayerPanel
                key={o.seat}
                p={o}
                isSelf={false}
                isCurrent={o.seat === view.current_player_seat}
                handCount={o.hand_count}
              />
            ))}
          </div>

          {/* Locations */}
          <div className="flex-1 flex flex-wrap justify-center gap-6 px-4 py-4">
            {view.locations.map((loc) => (
              <LocationPile
                key={loc.location}
                loc={loc}
                selectable={locTokens.has(loc.location)}
                onSelect={() => answer([locTokens.get(loc.location)!])}
              />
            ))}
          </div>

          {/* Your panel + hand */}
          <div className="px-4 pb-2">
            <div className="mb-2 max-w-xs">
              <PlayerPanel
                p={view.you}
                isSelf
                isCurrent={view.you.seat === view.current_player_seat}
                handCount={view.you.hand.length}
              />
            </div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              <AnimatePresence initial={false}>
                {view.you.hand.map((id, i) => (
                  <motion.div
                    key={`${id}-${i}`}
                    layout
                    initial={{ opacity: 0, y: 16, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.85 }}
                    transition={{ duration: 0.18 }}
                  >
                    <CardView
                      cardId={id}
                      size="md"
                      selectable={cardTokens.has(id)}
                      onClick={cardTokens.has(id) ? () => answer([cardTokens.get(id)!]) : undefined}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
              {view.you.hand.length === 0 && <span className="opacity-40 text-sm">empty hand</span>}
            </div>
          </div>

          {view.finished ? (
            <Scoreboard view={view} />
          ) : (
            !replay && (
              <DecisionBar
                pending={live?.pending ?? null}
                waiting={live?.waiting_on ?? null}
                onAnswer={answer}
              />
            )
          )}
        </div>

        {showLog && (
          <aside className="w-72 shrink-0 border-l border-white/10 bg-black/20 hidden md:flex flex-col">
            <EventLog events={events} nameOf={nameOf} />
          </aside>
        )}
      </div>
    </div>
  );
}

function ConnDot({ status }: { status: string }) {
  const color =
    status === "open" ? "bg-green-400" : status === "connecting" ? "bg-amber-400" : "bg-red-400";
  return (
    <span className="flex items-center gap-1 opacity-70" title={`Connection: ${status}`}>
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {status !== "open" && <span>{status}</span>}
    </span>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center opacity-70 px-6 text-center">
      {children}
    </div>
  );
}
