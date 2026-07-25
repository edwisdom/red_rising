import { useGame, type Creds } from "./store";

// A thin WebSocket wrapper with auto-reconnect. The server pushes the full
// redacted view on every change, so reconnecting just means "get the latest view"
// — there is no client-side game state to rebuild.
export class GameSocket {
  private ws: WebSocket | null = null;
  private closedByUs = false;
  private retry = 0;

  constructor(private creds: Creds) {}

  connect(): void {
    this.closedByUs = false;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const { gameId, seat, token } = this.creds;
    const url = `${proto}://${location.host}/ws/${gameId}?seat=${seat}&token=${encodeURIComponent(token)}`;
    useGame.getState().setStatus("connecting");
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.retry = 0;
      useGame.getState().setStatus("open");
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "view") {
        useGame.getState().setView(msg.view);
        if (msg.events) useGame.getState().applyEvents(msg.events, !!msg.reset);
        useGame.getState().setError(null);
      } else if (msg.type === "error") {
        useGame.getState().setError(msg.message);
      }
    };
    ws.onclose = (ev) => {
      useGame.getState().setStatus("closed");
      if (this.closedByUs) return;
      if (ev.code === 4403) {
        useGame.getState().setError("This game link is invalid or expired.");
        return;
      }
      // Exponential-ish backoff, capped, so a server blip self-heals.
      const delay = Math.min(1000 * 2 ** this.retry++, 8000);
      setTimeout(() => this.connect(), delay);
    };
  }

  answer(decisionId: number, tokens: string[]): void {
    this.ws?.send(JSON.stringify({ type: "answer", decision_id: decisionId, tokens }));
  }

  undo(): void {
    this.ws?.send(JSON.stringify({ type: "undo" }));
  }

  close(): void {
    this.closedByUs = true;
    this.ws?.close();
  }
}
