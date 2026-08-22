import { useEffect, useState } from "react";
import { loadCards } from "./cards";
import { CardZoomProvider } from "./components/CardZoom";
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

  if (!ready) return <Splash />;
  return (
    <CardZoomProvider>
      {route.kind === "lobby" ? <Lobby /> : <Game creds={route.creds} />}
    </CardZoomProvider>
  );
}

// The deck of 112 cards has to land before anything can render; give that beat a
// face rather than a bare "Loading…".
function Splash() {
  return (
    <div className="min-h-screen grid place-items-center">
      <div className="text-center">
        <div className="font-display text-3xl font-black tracking-[0.3em] text-amber-200/90 animate-pulse">
          RED RISING
        </div>
        <div className="mt-2 text-xs uppercase tracking-[0.35em] opacity-40">Dealing the deck</div>
      </div>
    </div>
  );
}
