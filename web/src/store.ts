import { create } from "zustand";
import type { PlayerView } from "./types";
import type { LogEvent } from "./eventText";

// Per-game credentials live in sessionStorage, NOT localStorage: the join link's
// token is the durable credential (it lives in the chat/email you were sent), and
// sessionStorage is per-tab, so two seats opened in one browser — or the creator's
// own two links — never clobber each other. A refresh keeps the tab's creds; a
// closed tab just reopens from the link.
export interface Creds {
  gameId: string;
  seat: string;
  token: string;
}

const credKey = (gameId: string) => `rr:game:${gameId}`;

export function saveCreds(c: Creds): void {
  sessionStorage.setItem(credKey(c.gameId), JSON.stringify({ seat: c.seat, token: c.token }));
}
export function loadCreds(gameId: string): Creds | null {
  const raw = sessionStorage.getItem(credKey(gameId));
  if (!raw) return null;
  const { seat, token } = JSON.parse(raw);
  return { gameId, seat, token };
}

type ConnStatus = "connecting" | "open" | "closed";

interface GameStore {
  view: PlayerView | null;
  events: LogEvent[]; // full running log for this seat (redacted server-side)
  status: ConnStatus;
  error: string | null;
  // Replay: when non-null, the UI shows a reconstructed past state instead of `view`.
  replay: { view: PlayerView; events: LogEvent[]; step: number; total: number } | null;
  setView: (v: PlayerView) => void;
  applyEvents: (events: LogEvent[], reset: boolean) => void;
  setStatus: (s: ConnStatus) => void;
  setError: (e: string | null) => void;
  setReplay: (r: GameStore["replay"]) => void;
}

export const useGame = create<GameStore>((set) => ({
  view: null,
  events: [],
  status: "connecting",
  error: null,
  replay: null,
  setView: (view) => set({ view }),
  applyEvents: (events, reset) =>
    set((s) => ({ events: reset ? events : [...s.events, ...events] })),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setReplay: (replay) => set({ replay }),
}));
