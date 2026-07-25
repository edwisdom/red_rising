import type { PendingDecision, WaitingOn } from "../types";

// The universal way to answer any decision: prompt + a button per option. Board
// and hand clicks (for location/card options) are a convenience layered on top in
// Game.tsx, but everything here is always answerable from these buttons alone.
export function DecisionBar({
  pending,
  waiting,
  onAnswer,
}: {
  pending: PendingDecision | null;
  waiting: WaitingOn | null;
  onAnswer: (tokens: string[]) => void;
}) {
  if (pending) {
    return (
      <div className="sticky bottom-0 bg-black/70 backdrop-blur border-t border-amber-400/40 px-4 py-3">
        <div className="text-sm font-semibold text-amber-200 mb-2">{pending.prompt}</div>
        <div className="flex flex-wrap gap-2">
          {pending.options.map((o) => (
            <button
              key={o.token}
              onClick={() => onAnswer([o.token])}
              className="px-3 py-1.5 rounded-md bg-amber-500/90 hover:bg-amber-400 text-black text-sm font-medium"
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    );
  }
  if (waiting) {
    return (
      <div className="sticky bottom-0 bg-black/60 backdrop-blur border-t border-white/10 px-4 py-3 text-sm opacity-80">
        Waiting for <span className="font-semibold">{waiting.name}</span>… ({waiting.prompt})
      </div>
    );
  }
  return null;
}
