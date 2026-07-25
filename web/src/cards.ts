import type { CardDef } from "./types";

// Caste display colors, mirroring `Color.hex` in the backend enums. The map is the
// single source for card banding, so light/dark both read consistently.
export const CASTE_HEX: Record<string, string> = {
  Red: "#c0392b",
  Pink: "#e78ba8",
  Orange: "#d97b2b",
  Yellow: "#d4b13a",
  Green: "#3f9e5a",
  Copper: "#a5673f",
  Silver: "#9aa4ad",
  Gold: "#c8a227",
  Blue: "#3a6ea5",
  Violet: "#8e5ba6",
  White: "#dfe3e6",
  Gray: "#6b7178",
  Brown: "#7a5230",
  Obsidian: "#2b2f33",
};

// Light text over dark bands, dark text over light ones.
export function textOn(color: string): string {
  return ["White", "Yellow", "Silver", "Pink"].includes(color) ? "#1a1a1a" : "#f5f5f5";
}

let CARD_INDEX: Map<string, CardDef> | null = null;

export async function loadCards(): Promise<Map<string, CardDef>> {
  if (CARD_INDEX) return CARD_INDEX;
  const res = await fetch("/api/cards");
  const data: { cards: CardDef[] } = await res.json();
  CARD_INDEX = new Map(data.cards.map((c) => [c.id, c]));
  return CARD_INDEX;
}

export function getCard(id: string): CardDef | undefined {
  return CARD_INDEX?.get(id);
}
