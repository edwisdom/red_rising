import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useGame, type Creds } from "../store";
import type { PlayerView } from "../types";
import { GameSocket } from "../ws";
import { CardView } from "./CardView";
import { HEADER_H, LocationPile } from "./LocationPile";
import { PlayerPanel } from "./PlayerPanel";
import { DecisionBar } from "./DecisionBar";
import { Scoreboard } from "./Scoreboard";
import { EventLog } from "./EventLog";
import { ReplayBar } from "./ReplayBar";
import { CardIndex } from "./CardIndex";
import { Zoomable } from "./CardZoom";
import { TurnHerald } from "./TurnHerald";
import { Icon } from "./Icons";
import { DECK_VIOLET } from "../theme";
import { useFitCards } from "../useBoardScale";
import { NARROW, useMediaQuery, WIDE } from "../useMediaQuery";

export function Game({ creds }: { creds: Creds }) {
  const live = useGame((s) => s.view);
  const liveEvents = useGame((s) => s.events);
  const replay = useGame((s) => s.replay);
  const setReplay = useGame((s) => s.setReplay);
  const status = useGame((s) => s.status);
  const error = useGame((s) => s.error);
  const sockRef = useRef<GameSocket | null>(null);
  const [showIndex, setShowIndex] = useState(false);
  // Below ~1100px the log costs the board more room than it is worth, so it
  // becomes an overlay you pull open instead of a column that squeezes the table.
  const wide = useMediaQuery(WIDE);
  // On a phone the fleet track's eleven pips are the widest thing in a panel and
  // the least readable; the VP number beside it says the same thing.
  const narrowPanels = useMediaQuery(NARROW);
  // Open by default only where it is free; on a narrow screen it would land as a
  // sheet over the board before you have done anything.
  const [logOpen, setLogOpen] = useState(
    () => typeof window !== "undefined" && window.matchMedia(WIDE).matches,
  );
  const showLog = logOpen && wide;
  const showLogDrawer = logOpen && !wide;

  useEffect(() => {
    const sock = new GameSocket(creds);
    sockRef.current = sock;
    sock.connect();
    return () => sock.close();
  }, [creds]);

  // "?" opens the card reference from anywhere — the digital equivalent of
  // reaching for the rulebook without putting your hand down.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "?" || (e.key === "/" && !e.metaKey && !e.ctrlKey)) {
        e.preventDefault();
        setShowIndex((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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

  const yourTurn = !replay && !!live?.pending;
  const hand = view.you.hand;

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden">
      <header className="shrink-0 flex items-center gap-3 px-3 sm:px-4 py-2 border-b border-white/10 bg-black/35 backdrop-blur-md">
        <span className="font-display font-black tracking-[0.22em] text-[15px] text-amber-200/90 shrink-0">
          RED&nbsp;RISING
        </span>
        <span className="hidden sm:flex items-center gap-2 text-[11px] uppercase tracking-wider opacity-55">
          <span>Turn {view.turn_number}</span>
        </span>
        <Pile
          count={view.deck_count}
          label="Deck"
          tint={DECK_VIOLET}
          icon={<Icon name="Deck" size={12} />}
        />
        <Pile
          count={view.banished.length}
          label="Banished"
          tint="#8c8c8c"
          icon={<Icon name="Banish" size={12} />}
        />
        <span className="flex-1" />
        <ConnDot status={status} />
        <HeaderBtn onClick={() => setShowIndex(true)} title="Browse all 112 cards (press ?)">
          Cards
        </HeaderBtn>
        {!replay && liveEvents.length > 0 && (
          <HeaderBtn onClick={() => sockRef.current?.undo()} title="Undo the last action">
            ↺<span className="hidden sm:inline"> Undo</span>
          </HeaderBtn>
        )}
        {!replay && (
          <HeaderBtn onClick={() => seekReplay(0)} title="Replay the game from the start">
            ⏮<span className="hidden sm:inline"> Replay</span>
          </HeaderBtn>
        )}
        <HeaderBtn onClick={() => setLogOpen((v) => !v)} title="Toggle the game log">
          {logOpen && wide ? "Hide log" : "Log"}
        </HeaderBtn>
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
          {/* Across the table */}
          <div className="flex flex-wrap gap-2 px-3 sm:px-4 pt-3 shrink-0">
            {view.opponents.map((o) => (
              <PlayerPanel
                key={o.seat}
                p={o}
                isSelf={false}
                isCurrent={o.seat === view.current_player_seat}
                handCount={o.hand_count}
                compact={narrowPanels}
              />
            ))}
          </div>

          {/* The board. One row of locations, sized to the room available, so a
              desktop window fills out and a phone still shows all four. */}
          <Board locations={view.locations} locTokens={locTokens} onSelect={(t) => answer([t])} />

          {/* Your side of the table */}
          <div className="flex-[2] min-h-[186px] flex flex-col border-t border-white/10 bg-black/30 backdrop-blur-sm">
            <div className="shrink-0 px-3 sm:px-4 pt-2 flex items-center gap-3 flex-wrap">
              <div className="min-w-[240px]">
                <PlayerPanel
                  p={view.you}
                  isSelf
                  isCurrent={view.you.seat === view.current_player_seat}
                  handCount={hand.length}
                  compact={narrowPanels}
                />
              </div>
              <span className="text-[10px] uppercase tracking-[0.18em] opacity-35 hidden sm:block">
                hover a card to read it · click to inspect
              </span>
            </div>
            <Hand hand={hand} cardTokens={cardTokens} onPlay={answer} yourTurn={yourTurn} />
          </div>

          {/* A finished game takes the screen for its own reveal, then folds down
              to a one-line result so the final board stays inspectable. */}
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

        <AnimatePresence initial={false}>
          {showLog && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 320, damping: 34 }}
              className="shrink-0 border-l border-white/10 bg-black/30 flex flex-col overflow-hidden"
            >
              <div className="w-[280px] flex-1 min-h-0 flex">
                <EventLog events={events} nameOf={nameOf} youSeat={view.you.seat} />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* Narrow screens get the log as a sheet over the table instead. */}
      <AnimatePresence>
        {showLogDrawer && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[60] bg-black/60"
              onClick={() => setLogOpen(false)}
            />
            <motion.aside
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 38 }}
              className="fixed top-0 right-0 bottom-0 z-[61] w-[min(320px,85vw)] border-l border-white/10 bg-[#120b0d] flex flex-col"
            >
              <button
                onClick={() => setLogOpen(false)}
                className="self-end m-2 px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[12px]"
              >
                Close
              </button>
              <div className="flex-1 min-h-0 flex">
                <EventLog events={events} nameOf={nameOf} youSeat={view.you.seat} />
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <TurnHerald
        yourTurn={yourTurn}
        yourName={view.you.name}
        waitingOn={live?.waiting_on?.name ?? null}
        finished={view.finished}
      />
      <CardIndex open={showIndex} onClose={() => setShowIndex(false)} />
    </div>
  );
}

// The four locations, sized as one unit so they always read as a single table.
function Board({
  locations,
  locTokens,
  onSelect,
}: {
  locations: PlayerView["locations"];
  locTokens: Map<string, string>;
  onSelect: (token: string) => void;
}) {
  const tallest = Math.max(1, ...locations.map((l) => l.cards.length));
  // On a phone the four locations in one row would each be at their floor with
  // most of the screen's height unused. Two by two trades the horizontal scroll
  // for cards you can actually read.
  const narrow = useMediaQuery(NARROW);
  const cols = narrow ? 2 : locations.length;
  const { ref, cardWidth } = useFitCards({
    lanes: cols,
    rows: Math.ceil(locations.length / cols),
    stack: tallest,
    gap: narrow ? 10 : 24,
    chrome: HEADER_H + 22, // label block + plinth padding + the row's own gap
    lanePad: 16,
    min: narrow ? 92 : 80,
    max: 210,
  });
  // A floor on each region, so a short window shrinks the board (which can
  // scroll) rather than crushing the hand (which cannot).
  return (
    <div
      ref={ref}
      className="flex-[3] min-h-[150px] flex items-center justify-center overflow-auto thin-scroll px-3 sm:px-4 py-2"
    >
      <div
        className="grid gap-2.5 sm:gap-6 justify-center"
        style={{ gridTemplateColumns: `repeat(${cols}, max-content)` }}
      >
        {locations.map((loc) => (
          <LocationPile
            key={loc.location}
            loc={loc}
            width={cardWidth}
            selectable={locTokens.has(loc.location)}
            onSelect={() => onSelect(locTokens.get(loc.location)!)}
          />
        ))}
      </div>
    </div>
  );
}

// Your hand, laid out with a slight arc so it reads as cards held rather than a
// row of tiles. Playable cards are lit; every card can be read on hover.
function Hand({
  hand,
  cardTokens,
  onPlay,
  yourTurn,
}: {
  hand: string[];
  cardTokens: Map<string, string>;
  onPlay: (tokens: string[]) => void;
  yourTurn: boolean;
}) {
  const mid = (hand.length - 1) / 2;
  const { ref, cardWidth } = useFitCards({
    lanes: Math.max(hand.length, 4),
    gap: 8,
    chrome: 26, // the lift and the arc need headroom inside the scroller
    lanePad: 0,
    min: 76,
    max: 176,
  });
  return (
    <div
      ref={ref}
      className="flex-1 min-h-0 flex gap-2 overflow-x-auto overflow-y-hidden thin-scroll px-3 sm:px-4 pt-3 pb-2 items-center"
    >
      <AnimatePresence initial={false}>
        {hand.map((id, i) => {
          const playable = cardTokens.has(id);
          const off = hand.length > 1 ? (i - mid) / Math.max(mid, 1) : 0;
          return (
            <motion.div
              key={`${id}-${i}`}
              layout
              initial={{ opacity: 0, y: 40, scale: 0.85 }}
              animate={{
                opacity: 1,
                y: Math.abs(off) * 5,
                rotate: off * 2,
                scale: 1,
              }}
              exit={{ opacity: 0, y: -60, scale: 0.8, transition: { duration: 0.25 } }}
              transition={{ type: "spring", stiffness: 340, damping: 30, delay: i * 0.03 }}
              className="origin-bottom"
            >
              <Zoomable cardId={id} list={hand} disabled={playable && yourTurn}>
                <CardView
                  cardId={id}
                  width={cardWidth}
                  selectable={playable}
                  onClick={playable ? () => onPlay([cardTokens.get(id)!]) : undefined}
                />
              </Zoomable>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {hand.length === 0 && (
        <span className="opacity-35 text-sm py-8">Your hand is empty.</span>
      )}
    </div>
  );
}

// The deck and banished piles, sized so you can feel the deck draining.
function Pile({
  count,
  label,
  tint,
  icon,
}: {
  count: number;
  label: string;
  tint: string;
  icon: React.ReactNode;
}) {
  return (
    <span
      className="hidden sm:inline-flex items-center gap-1.5 rounded-md px-2 py-1 leading-none"
      style={{ background: `${tint}15`, boxShadow: `inset 0 0 0 1px ${tint}35` }}
      title={`${count} cards ${label.toLowerCase()}`}
    >
      <span style={{ color: tint }}>{icon}</span>
      <span className="text-[11px] uppercase tracking-wide opacity-55">{label}</span>
      <span className="text-[12px] font-semibold tabular-nums">{count}</span>
    </span>
  );
}

function HeaderBtn({
  onClick,
  title,
  children,
}: {
  onClick: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="shrink-0 px-2.5 py-1 rounded-lg bg-white/8 hover:bg-white/18 text-[12px] font-medium transition"
    >
      {children}
    </button>
  );
}

function ConnDot({ status }: { status: string }) {
  const color =
    status === "open" ? "bg-green-400" : status === "connecting" ? "bg-amber-400" : "bg-red-400";
  return (
    <span className="flex items-center gap-1 text-[11px] opacity-70" title={`Connection: ${status}`}>
      <span className={`w-2 h-2 rounded-full ${color} ${status !== "open" ? "pulse-ring" : ""}`} />
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
