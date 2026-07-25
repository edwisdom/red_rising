import type { OpponentView, SelfView } from "../types";

// Compact resource readout for one player. Works for both your own panel and an
// opponent's (an opponent has a hand count instead of visible cards).
export function PlayerPanel({
  p,
  isSelf,
  isCurrent,
  handCount,
}: {
  p: SelfView | OpponentView;
  isSelf: boolean;
  isCurrent: boolean;
  handCount: number;
}) {
  return (
    <div
      className={`rounded-lg px-3 py-2 border ${
        isCurrent ? "border-amber-400/80 bg-amber-400/10" : "border-white/10 bg-black/20"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold">{p.name}</span>
        <span className="text-xs uppercase tracking-wide opacity-60">{p.house}</span>
        {isSelf && <span className="text-xs opacity-60">(you)</span>}
        {p.has_sovereign && <span title="Sovereign">👑</span>}
        {isCurrent && <span className="text-xs text-amber-300">● turn</span>}
      </div>
      <div className="flex gap-3 mt-1 text-sm tabular-nums">
        <span title="Helium">💎 {p.helium}</span>
        <span title="Fleet Track">🚀 {p.fleet}</span>
        <span title="Influence on the Institute">🏛️ {p.influence_on_institute}</span>
        <span title="Cards in hand">🂠 {handCount}</span>
      </div>
    </div>
  );
}
