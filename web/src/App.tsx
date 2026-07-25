import { useEffect, useState } from "react";
import { loadCards } from "./cards";
import { Lobby } from "./components/Lobby";
import { Game } from "./components/Game";
import { loadCreds, saveCreds, type Creds } from "./store";

// Minimal routing without a router dependency:
//   /                       -> Lobby (create a game)
//   /g/<id>?seat=&token=    -> Game (join link; creds get saved, then stripped)
//   /g/<id>                 -> Game (reuse saved creds)
function resolveRoute(): { kind: "lobby" } | { kind: "game"; creds: Creds } {
  const m = location.pathname.match(/^\/g\/([^/]+)/);
  if (!m) return { kind: "lobby" };
  const gameId = m[1];
  const params = new URLSearchParams(location.search);
  const seat = params.get("seat");
  const token = params.get("token");
  if (seat && token) {
    const creds = { gameId, seat, token };
    saveCreds(creds);
    // Drop the token from the address bar once it's saved.
    history.replaceState(null, "", `/g/${gameId}`);
    return { kind: "game", creds };
  }
  const saved = loadCreds(gameId);
  if (saved) return { kind: "game", creds: saved };
  return { kind: "lobby" };
}

export function App() {
  const [ready, setReady] = useState(false);
  const [route] = useState(resolveRoute);

  useEffect(() => {
    loadCards().then(() => setReady(true));
  }, []);

  if (!ready) return <div className="p-8 text-center opacity-60">Loading…</div>;
  if (route.kind === "lobby") return <Lobby />;
  return <Game creds={route.creds} />;
}
