import { getCard } from "./cards";

// Raw events arrive as loosely-typed dicts (a discriminated union on `type`). We
// only read the fields each branch needs.
export type LogEvent = Record<string, any> & { type: string; seq: number };

const LOC: Record<string, string> = {
  Jupiter: "Jupiter",
  Mars: "Mars",
  Luna: "Luna",
  Institute: "the Institute",
};

const FACE: Record<string, string> = {
  banish: "❌ Banish",
  reveal: "👁️ Reveal",
  sovereign: "👑 Sovereign",
  helium: "💎 Helium",
  fleet: "🚀 Fleet",
  influence: "🏛️ Influence",
};

export interface LogLine {
  seq: number;
  kind: "divider" | "entry";
  icon: string;
  text: string;
}

const cardName = (id: string | null | undefined) => (id ? (getCard(id)?.name ?? id) : "a card");

// Map an event to a log line, or null to hide it (folded-in or noise).
export function describeEvent(ev: LogEvent, nameOf: (seat: string) => string): LogLine | null {
  const line = (kind: LogLine["kind"], icon: string, text: string): LogLine => ({
    seq: ev.seq,
    kind,
    icon,
    text,
  });

  switch (ev.type) {
    case "turn_began":
      return line("divider", "", `${nameOf(ev.seat)} · turn ${ev.turn_number}`);
    case "deployed":
      return line("entry", "⚡", `${nameOf(ev.seat)} deployed ${cardName(ev.card_id)} on ${LOC[ev.location]}`);
    case "placed":
      return line("entry", "🃏", `${nameOf(ev.seat)} placed ${cardName(ev.card_id)} on ${LOC[ev.location]}`);
    case "card_gained":
      return line("entry", "➕", `${nameOf(ev.seat)} gained ${cardName(ev.card_id)}`);
    case "banished":
      return line("entry", "❌", `${cardName(ev.card_id)} was banished`);
    case "card_moved":
      return line("entry", "↦", `${cardName(ev.card_id)} moved to ${LOC[ev.to_location]}`);
    case "card_stolen":
      return line(
        "entry",
        "🫳",
        `${nameOf(ev.to_seat)} stole ${cardName(ev.card_id)} from ${nameOf(ev.from_seat)}`,
      );
    case "blocked":
      return line("entry", "🛡️", `${nameOf(ev.seat)} blocked with ${cardName(ev.block_card)}`);
    case "die_rolled":
      return line("entry", "🎲", `${nameOf(ev.seat)} rolled ${FACE[ev.face] ?? ev.face}`);
    case "sovereign_changed":
      return line("entry", "👑", `${nameOf(ev.seat)} took the Sovereign token`);
    case "game_end_triggered":
      return line("divider", "⚑", `Endgame triggered by ${nameOf(ev.by_seat)}`);
    case "game_ended": {
      const who = (ev.winners as string[]).map(nameOf).join(" & ");
      return line("divider", "🏆", `Game over — ${who} wins`);
    }
    default:
      return null; // setup, resource deltas, house ability, decision bookkeeping
  }
}
