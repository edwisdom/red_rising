import type { PlayerView, ScoreBreakdown } from "../types";
import { scoreTotal } from "../types";

const ROWS: [keyof ScoreBreakdown, string][] = [
  ["core_values", "Core values"],
  ["card_bonuses", "Card bonuses"],
  ["fleet", "Fleet Track"],
  ["helium", "Helium ×3"],
  ["sovereignty", "Sovereignty"],
  ["influence", "Influence"],
  ["excess_penalty", "Excess cards"],
];

export function Scoreboard({ view }: { view: PlayerView }) {
  if (!view.scores) return null;
  const seats = Object.keys(view.scores);
  const nameOf = (seat: string) =>
    seat === view.you.seat ? view.you.name : view.opponents.find((o) => o.seat === seat)?.name ?? seat;
  const totals = Object.fromEntries(seats.map((s) => [s, scoreTotal(view.scores![s])]));
  const best = Math.max(...Object.values(totals));

  return (
    <div className="max-w-2xl mx-auto mt-8 rounded-xl border border-white/10 bg-black/40 p-6">
      <h2 className="text-2xl font-bold mb-1">Final score</h2>
      <p className="opacity-60 text-sm mb-4">A great final score is 300+.</p>
      <table className="w-full text-sm tabular-nums">
        <thead>
          <tr className="text-left opacity-60">
            <th className="py-1">Category</th>
            {seats.map((s) => (
              <th key={s} className="py-1 text-right">
                {nameOf(s)}
                {totals[s] === best && " 🏆"}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([key, label]) => (
            <tr key={key} className="border-t border-white/5">
              <td className="py-1 opacity-80">{label}</td>
              {seats.map((s) => (
                <td key={s} className="py-1 text-right">
                  {view.scores![s][key] as number}
                </td>
              ))}
            </tr>
          ))}
          <tr className="border-t-2 border-white/20 font-bold">
            <td className="py-2">Total</td>
            {seats.map((s) => (
              <td key={s} className="py-2 text-right text-amber-300">
                {totals[s]}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
