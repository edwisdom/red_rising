// Scrubber for stepping through a finished (or in-progress) game. `step` counts
// answers applied; 0 is the opening position, `total` is now.
export function ReplayBar({
  step,
  total,
  onSeek,
  onExit,
}: {
  step: number;
  total: number;
  onSeek: (step: number) => void;
  onExit: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-amber-500/10 border-b border-amber-400/40 text-sm">
      <span className="font-semibold text-amber-200">Replay</span>
      <button
        onClick={() => onSeek(Math.max(0, step - 1))}
        className="px-2 rounded bg-white/10 hover:bg-white/20"
        aria-label="Step back"
      >
        ◀
      </button>
      <input
        type="range"
        min={0}
        max={total}
        value={step}
        onChange={(e) => onSeek(Number(e.target.value))}
        className="flex-1 accent-amber-400"
      />
      <button
        onClick={() => onSeek(Math.min(total, step + 1))}
        className="px-2 rounded bg-white/10 hover:bg-white/20"
        aria-label="Step forward"
      >
        ▶
      </button>
      <span className="tabular-nums opacity-70">
        {step} / {total}
      </span>
      <button onClick={onExit} className="px-3 py-1 rounded bg-amber-500 text-black font-medium">
        Exit
      </button>
    </div>
  );
}
