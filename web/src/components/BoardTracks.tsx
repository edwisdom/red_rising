import { AnimatePresence, motion } from "framer-motion";
import type { OpponentView, PlayerView, SelfView } from "../types";
import { FLEET_TRACK_POINTS, MAX_INFLUENCE, influenceRate } from "../types";
import { LOCATION, seatColor } from "../theme";
import { useChanged } from "../useChanged";
import { Icon } from "./Icons";
import { Counter } from "./Tokens";

// The Fleet Track and the Institute's influence are the two things in this game
// that only mean anything *relative to your opponent*. On the physical board they
// are shared spaces with everybody's tokens sitting on them — not numbers in each
// player's corner — so reading them off two opposite ends of the screen turned
// the one comparison that matters into a memory test. They live here instead:
// one strip, both players, read the same way by both.

interface Player {
  seat: string;
  name: string;
  fleet: number;
  influence_on_institute: number;
}

/** Seat order, never "me first" — both players must see the same arrangement. */
function seated(view: PlayerView): Player[] {
  const all: (SelfView | OpponentView)[] = [view.you, ...view.opponents];
  return all
    .map((p) => ({
      seat: p.seat,
      name: p.name,
      fleet: p.fleet,
      influence_on_institute: p.influence_on_institute,
    }))
    .sort((a, b) => a.seat.localeCompare(b.seat));
}

export function BoardTracks({ view, compact }: { view: PlayerView; compact?: boolean }) {
  const players = seated(view);
  return (
    <div className="shrink-0 flex flex-wrap justify-center items-start gap-2 px-3 sm:px-4 pb-1.5">
      <FleetTrack players={players} youSeat={view.you.seat} compact={compact} />
      <Influence
        players={players}
        neutral={view.neutral_influence}
        youSeat={view.you.seat}
        compact={compact}
      />
    </div>
  );
}

// ── Fleet Track ──────────────────────────────────────────────────────────────
// Eleven printed spaces with their VP value, and a token standing on the space
// each player has reached. Discrete spaces rather than a bare rail: the payout
// curve is steep and uneven (0,1,3,6,10,15,21,28,34,39,43), so "two spaces
// ahead" means nothing on its own and you need to read the numbers you passed.
function FleetTrack({
  players,
  youSeat,
  compact,
}: {
  players: Player[];
  youSeat: string;
  compact?: boolean;
}) {
  const blue = LOCATION.Jupiter.color;
  const box = compact ? 21 : 27;
  const gap = compact ? 2 : 3;
  const lead = Math.max(...players.map((p) => p.fleet));

  return (
    <Panel tint={blue} icon={<Icon name="Jupiter" size={15} />} label="Fleet Track">
      <div className="relative" style={{ paddingTop: compact ? 13 : 15 }}>
        <div className="flex shrink-0" style={{ gap }}>
          {FLEET_TRACK_POINTS.map((pts, i) => {
            const reached = i <= lead;
            return (
              <span
                key={i}
                className="grid place-items-center rounded-[3px] tabular-nums font-semibold"
                style={{
                  // The token is positioned by arithmetic on this width, so the
                  // space must not shrink under flex pressure or the marker
                  // drifts off the space it is standing on.
                  flexShrink: 0,
                  width: box,
                  height: compact ? 17 : 20,
                  fontSize: compact ? 8.5 : 10,
                  background: reached ? `${blue}2b` : "rgba(255,255,255,.045)",
                  boxShadow: `inset 0 0 0 1px ${reached ? `${blue}55` : "rgba(255,255,255,.08)"}`,
                  color: reached ? "#dbeeff" : "rgba(255,255,255,.35)",
                }}
                title={`Space ${i} — ${pts} VP`}
              >
                {pts}
              </span>
            );
          })}
        </div>

        {players.map((p) => (
          <FleetToken
            key={p.seat}
            p={p}
            youSeat={youSeat}
            box={box}
            gap={gap}
            compact={compact}
            sharing={players.filter((q) => q.fleet === p.fleet)}
          />
        ))}
      </div>
    </Panel>
  );
}

function FleetToken({
  p,
  youSeat,
  box,
  gap,
  compact,
  sharing,
}: {
  p: Player;
  youSeat: string;
  box: number;
  gap: number;
  compact?: boolean;
  sharing: Player[];
}) {
  const c = seatColor(p.seat);
  const size = compact ? 15 : 18;
  const moved = useChanged(p.fleet);
  // Two tokens on one space would sit on top of each other; fan them instead.
  const nth = sharing.indexOf(p);
  const nudge = sharing.length > 1 ? (nth - (sharing.length - 1) / 2) * (size * 0.55) : 0;
  const isYou = p.seat === youSeat;

  return (
    <motion.span
      className="absolute top-0 grid place-items-center rounded-full font-bold"
      style={{
        width: size,
        height: size,
        marginLeft: (box - size) / 2,
        fontSize: compact ? 8.5 : 10,
        background: `radial-gradient(circle at 32% 26%, ${c}, ${c}aa)`,
        color: "#180f12",
        zIndex: 2,
      }}
      initial={false}
      // The token travels the spaces it actually gained — that journey is the
      // whole reason this is a track and not a number.
      animate={{
        left: p.fleet * (box + gap) + nudge,
        boxShadow: moved
          ? `0 0 0 1.5px rgba(0,0,0,.55), 0 0 14px 3px ${c}`
          : `0 0 0 1.5px rgba(0,0,0,.55), 0 0 6px ${c}66`,
        scale: moved ? 1.18 : 1,
      }}
      transition={{
        left: { type: "spring", stiffness: 240, damping: 22 },
        scale: { type: "spring", stiffness: 500, damping: 15 },
        boxShadow: { duration: 0.25 },
      }}
      title={`${p.name} — space ${p.fleet}, worth ${FLEET_TRACK_POINTS[p.fleet]} VP`}
    >
      {p.name.slice(0, 1).toUpperCase()}
      {isYou && (
        <span
          className="absolute rounded-full pointer-events-none"
          style={{ inset: -3, boxShadow: `0 0 0 1.5px ${c}` }}
        />
      )}
    </motion.span>
  );
}

// ── Institute influence ──────────────────────────────────────────────────────
// Tokens sit on the Institute on the real board. What they are worth depends
// entirely on who has the most, so the rate is shown alongside the count — the
// 4/2/1 majority rule is the least memorable scoring rule in the game, and the
// neutral house shifts the tiers without scoring anything itself.
function Influence({
  players,
  neutral,
  youSeat,
  compact,
}: {
  players: Player[];
  neutral: number;
  youSeat: string;
  compact?: boolean;
}) {
  const green = LOCATION.Institute.color;
  const counts = [
    ...players.map((p) => p.influence_on_institute),
    ...(neutral > 0 ? [neutral] : []),
  ];
  const rows = [
    ...players.map((p) => ({
      key: p.seat,
      name: p.name,
      count: p.influence_on_institute,
      color: seatColor(p.seat),
      you: p.seat === youSeat,
      scores: true,
    })),
    ...(neutral > 0
      ? [{ key: "neutral", name: "Neutral", count: neutral, color: "#7c7c7c", you: false, scores: false }]
      : []),
  ];

  return (
    <Panel tint={green} icon={<Icon name="Institute" size={15} />} label="Influence">
      <div className="flex flex-col gap-[3px]">
        {rows.map((r) => (
          <InfluenceRow
            {...r}
            key={r.key}
            rate={r.scores ? influenceRate(r.count, counts) : 0}
            compact={compact}
            green={green}
          />
        ))}
      </div>
    </Panel>
  );
}

function InfluenceRow({
  name,
  count,
  color,
  you,
  scores,
  rate,
  compact,
  green,
}: {
  name: string;
  count: number;
  color: string;
  you: boolean;
  scores: boolean;
  rate: number;
  compact?: boolean;
  green: string;
}) {
  const moved = useChanged(count);
  const cube = compact ? 6 : 8;

  return (
    <div className="flex items-center gap-1.5 leading-none">
      <span
        className="text-[10px] uppercase tracking-wide truncate shrink-0"
        style={{ width: compact ? 42 : 54, color: you ? color : "rgba(255,255,255,.5)" }}
        title={name}
      >
        {name}
      </span>
      {/* Only the tokens actually placed, at a size you can count. Ten dim
          placeholder slots per row read as noise at this scale, and a pile of
          cubes on the real board compares by how long the row is. The track
          keeps a fixed width so gaining one does not shove the panel sideways. */}
      <span
        className="flex gap-[2.5px] items-center shrink-0"
        style={{ width: MAX_INFLUENCE * (cube + 2.5) }}
      >
        <AnimatePresence initial={false}>
          {Array.from({ length: count }, (_, i) => (
            <motion.span
              key={i}
              // A placed token drops onto the Institute and settles.
              initial={{ scale: 0.2, opacity: 0, y: -8 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.2, opacity: 0 }}
              transition={{ type: "spring", stiffness: 440, damping: 16 }}
              style={{
                width: cube,
                height: cube,
                borderRadius: 1.5,
                display: "block",
                flexShrink: 0,
                background: `linear-gradient(140deg, ${color}, ${color}88)`,
                boxShadow: `0 0 0 0.5px rgba(0,0,0,.45), 0 0 6px ${color}77`,
              }}
            />
          ))}
        </AnimatePresence>
        {count === 0 && <span className="text-[9px] opacity-25">—</span>}
      </span>
      {scores && (
        <motion.span
          className="text-[9px] tabular-nums shrink-0 rounded px-1 py-[1px] font-bold"
          animate={{ scale: moved ? 1.15 : 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 14 }}
          style={{
            background: rate === 4 ? `${green}3a` : "rgba(255,255,255,.06)",
            color: rate === 4 ? "#c3f0a6" : "rgba(255,255,255,.5)",
          }}
          title={`Each token scores ${rate} VP — 4 for the most, 2 for second, 1 otherwise`}
        >
          ×{rate}
        </motion.span>
      )}
      <span className="text-[10px] tabular-nums opacity-65 w-6 text-right shrink-0">
        {scores ? <Counter value={count * rate} /> : count}
      </span>
    </div>
  );
}

// ── shared chrome ────────────────────────────────────────────────────────────
// The label sits beside the content, not above it: vertical space here comes
// straight out of the board's card size, and there is width to spare.
function Panel({
  tint,
  icon,
  label,
  children,
}: {
  tint: string;
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-xl pl-2 pr-2.5 py-1.5 min-w-0 flex items-center gap-2"
      style={{
        background: `linear-gradient(${tint}12, rgba(0,0,0,.28))`,
        boxShadow: `inset 0 0 0 1px ${tint}2e`,
      }}
    >
      <span
        className="flex flex-col items-center gap-0.5 shrink-0"
        style={{ color: tint, width: 34 }}
      >
        {icon}
        <span className="font-display text-[7.5px] font-bold uppercase tracking-[0.12em] text-center leading-[1.15]">
          {label}
        </span>
      </span>
      <span className="min-w-0">{children}</span>
    </div>
  );
}
