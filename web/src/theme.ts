// The real game's palette, lifted from the official rules reference so the digital
// table matches the printed cards. Every caste has a base and a darker "shade" —
// physical card headers are a radial gradient between the two, which is what makes
// them read as embossed rather than flat.
export interface Caste {
  base: string;
  shade: string;
  ink: string; // text that sits on the caste gradient
}

export const CASTE: Record<string, Caste> = {
  Red: { base: "#c6102e", shade: "#8e0b21", ink: "#fff" },
  Pink: { base: "#e76592", shade: "#d84680", ink: "#3f2029" },
  Orange: { base: "#f15d27", shade: "#be4519", ink: "#fff" },
  Yellow: { base: "#fff480", shade: "#e5b60b", ink: "#3f3f40" },
  Green: { base: "#61b545", shade: "#267840", ink: "#fff" },
  Copper: { base: "#a56027", shade: "#803519", ink: "#fff" },
  Silver: { base: "#cedde4", shade: "#8e9ca4", ink: "#2a3238" },
  Gold: { base: "#e4b50c", shade: "#a27106", ink: "#3f2f05" },
  Blue: { base: "#1dbccd", shade: "#00558a", ink: "#fff" },
  Violet: { base: "#7c59a6", shade: "#663091", ink: "#fff" },
  White: { base: "#ffffff", shade: "#e4e2e2", ink: "#3f3f40" },
  Gray: { base: "#78706d", shade: "#5c5451", ink: "#fff" },
  Brown: { base: "#622d09", shade: "#4b2001", ink: "#fff" },
  Obsidian: { base: "#363536", shade: "#252223", ink: "#fff" },
};

const FALLBACK: Caste = { base: "#5b5b5b", shade: "#3a3a3a", ink: "#fff" };

export function caste(color: string): Caste {
  return CASTE[color] ?? FALLBACK;
}

// The embossed header gradient the printed cards use.
export function casteGradient(color: string): string {
  const c = caste(color);
  return `radial-gradient(circle at 30% 25%, ${c.base}, ${c.shade})`;
}

// The four locations carry their own signature colors on the board.
export const LOCATION: Record<string, { color: string; glow: string; bonus: string }> = {
  Jupiter: { color: "#0071eb", glow: "#0071eb", bonus: "Advance on the Fleet Track" },
  Mars: { color: "#c6102e", glow: "#c6102e", bonus: "Gain 1 Helium" },
  Luna: { color: "#ffb61a", glow: "#ffb61a", bonus: "Gain the Sovereign token" },
  Institute: { color: "#4c8c2b", glow: "#4c8c2b", bonus: "Place 1 Influence" },
};

export const DECK_VIOLET = "#ad1aad";

export const LOCATION_LABEL: Record<string, string> = { Institute: "The Institute" };

// Player identity. Assigned by SEAT, never by "is this me", so both players see
// the same person in the same colour and can talk about "the cyan marker".
// Chosen to sit clear of the four location colours and to stay legible as a 10px
// token on the felt.
const SEAT_COLORS = ["#ff9f4a", "#4fd2e8", "#c98bff", "#7ee787", "#ff7ab8", "#ffe066"];

export function seatColor(seat: string): string {
  const n = Number(seat.replace(/\D/g, ""));
  return SEAT_COLORS[(Number.isFinite(n) ? n : 0) % SEAT_COLORS.length];
}

// Portraits are vendored under web/public/characters/<card id>.webp.
export function portrait(cardId: string): string {
  return `/characters/${cardId}.webp`;
}
