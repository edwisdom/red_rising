import { getCard } from "./cards";
import type { IconName } from "./components/Icons";

// Raw events arrive as loosely-typed dicts (a discriminated union on `type`). We
// only read the fields each branch needs.
export type LogEvent = Record<string, any> & { type: string; seq: number };

const LOC: Record<string, string> = {
  Jupiter: "Jupiter",
  Mars: "Mars",
  Luna: "Luna",
  Institute: "the Institute",
};

// What each die face gives you, in the game's own icons.
const FACE: Record<string, { icon: IconName; label: string }> = {
  banish: { icon: "Banish", label: "Banish" },
  reveal: { icon: "Deck", label: "Reveal" },
  sovereign: { icon: "Luna", label: "the Sovereign" },
  helium: { icon: "Mars", label: "Helium" },
  fleet: { icon: "Jupiter", label: "Fleet" },
  influence: { icon: "Institute", label: "Influence" },
};

export interface LogLine {
  seq: number;
  kind: "divider" | "entry";
  /** One of the game's own icons, when the event maps to a game concept. */
  icon: IconName | null;
  /** The card this line is about — the log shows its portrait. */
  cardId?: string | null;
  /** Whose action this is, so your own moves can read differently. */
  seat?: string | null;
  text: string;
}

const cardName = (id: string | null | undefined) => (id ? (getCard(id)?.name ?? id) : "a card");

// Map an event to a log line, or null to hide it (folded-in or noise).
export function describeEvent(ev: LogEvent, nameOf: (seat: string) => string): LogLine | null {
  const line = (
    kind: LogLine["kind"],
    icon: IconName | null,
    text: string,
    extra: Partial<LogLine> = {},
  ): LogLine => ({ seq: ev.seq, kind, icon, text, ...extra });

  switch (ev.type) {
    case "turn_began":
      return line("divider", null, `${nameOf(ev.seat)} · turn ${ev.turn_number}`, { seat: ev.seat });
    case "deployed":
      return line("entry", "Deploy", `deployed ${cardName(ev.card_id)} on ${LOC[ev.location]}`, {
        cardId: ev.card_id,
        seat: ev.seat,
      });
    case "placed":
      return line("entry", "Deck", `placed ${cardName(ev.card_id)} on ${LOC[ev.location]}`, {
        cardId: ev.card_id,
        seat: ev.seat,
      });
    case "card_gained":
      return line("entry", null, `gained ${cardName(ev.card_id)}`, {
        cardId: ev.card_id,
        seat: ev.seat,
      });
    case "banished":
      return line("entry", "Banish", `${cardName(ev.card_id)} was banished`, {
        cardId: ev.card_id,
      });
    case "card_moved":
      return line("entry", null, `${cardName(ev.card_id)} moved to ${LOC[ev.to_location]}`, {
        cardId: ev.card_id,
      });
    case "card_stolen":
      return line(
        "entry",
        null,
        `stole ${cardName(ev.card_id)} from ${nameOf(ev.from_seat)}`,
        { cardId: ev.card_id, seat: ev.to_seat },
      );
    case "blocked":
      return line("entry", "Block", `blocked with ${cardName(ev.block_card)}`, {
        cardId: ev.block_card,
        seat: ev.seat,
      });
    case "die_rolled": {
      const f = FACE[ev.face];
      return line("entry", f?.icon ?? null, `rolled ${f?.label ?? ev.face}`, { seat: ev.seat });
    }
    case "sovereign_changed":
      return line("entry", "Luna", `took the Sovereign token`, { seat: ev.seat });
    case "game_end_triggered":
      return line("divider", "EndGame", `Endgame triggered by ${nameOf(ev.by_seat)}`);
    case "game_ended": {
      const who = (ev.winners as string[]).map(nameOf).join(" & ");
      return line("divider", "EndGame", `Game over — ${who} wins`);
    }
    default:
      return null; // setup, resource deltas, house ability, decision bookkeeping
  }
}
