import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { allCards } from "../cards";
import { saveCreds } from "../store";
import { casteGradient, portrait } from "../theme";
import { CardIndex } from "./CardIndex";

interface SeatOut {
  seat: string;
  name: string;
  token: string;
}
interface CreateResponse {
  game_id: string;
  seats: SeatOut[];
}

// Create a 2-player game. The creator takes seat p0 and gets a link to send the
// partner (seat p1). No accounts: the link's token is the credential.
export function Lobby() {
  const [you, setYou] = useState("");
  const [partner, setPartner] = useState("");
  const [created, setCreated] = useState<CreateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showIndex, setShowIndex] = useState(false);

  const create = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/games", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          players: [{ name: you || "You" }, { name: partner || "Partner" }],
        }),
      });
      const data: CreateResponse = await res.json();
      saveCreds({ gameId: data.game_id, seat: "p0", token: data.seats[0].token });
      setCreated(data);
    } finally {
      setBusy(false);
    }
  };

  const p1 = created?.seats[1];
  const link = created
    ? `${location.origin}/g/${created.game_id}?seat=p1&token=${encodeURIComponent(p1!.token)}`
    : "";

  const copy = async () => {
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <Shell onBrowse={() => setShowIndex(true)}>
      {created ? (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h2 className="font-display text-2xl font-bold mb-1">The table is set</h2>
          <p className="opacity-60 text-sm mb-5">
            Send this private link to {p1!.name}. It is their seat and their credential — anyone
            holding it can play as them.
          </p>
          <div className="flex gap-2 mb-5">
            <input
              readOnly
              value={link}
              onFocus={(e) => e.currentTarget.select()}
              className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-black/50 border border-white/10 text-xs font-mono"
            />
            <button
              onClick={copy}
              className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm shrink-0 transition"
            >
              {copied ? "Copied ✓" : "Copy"}
            </button>
          </div>
          <a
            href={`/g/${created.game_id}`}
            className="inline-block px-5 py-2.5 rounded-lg font-semibold text-black transition"
            style={{
              background: "linear-gradient(#f0c85e, #c9962a)",
              boxShadow: "0 6px 18px rgba(232,188,85,.3)",
            }}
          >
            Take your seat →
          </a>
        </motion.div>
      ) : (
        <>
          <p className="opacity-55 text-sm mb-6 leading-relaxed">
            A two-player table. Deal 112 characters of the Society across Jupiter, Mars, Luna and
            the Institute, and see who reads the board better.
          </p>
          <div className="space-y-3">
            <Field label="Your name" value={you} onChange={setYou} placeholder="You" />
            <Field
              label="Partner's name"
              value={partner}
              onChange={setPartner}
              placeholder="Partner"
            />
            <motion.button
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
              onClick={create}
              disabled={busy}
              className="w-full px-4 py-2.5 rounded-lg font-semibold text-black disabled:opacity-50 transition"
              style={{
                background: "linear-gradient(#f0c85e, #c9962a)",
                boxShadow: "0 6px 18px rgba(232,188,85,.28)",
              }}
            >
              {busy ? "Shuffling…" : "Deal a new game"}
            </motion.button>
          </div>
        </>
      )}
      <CardIndex open={showIndex} onClose={() => setShowIndex(false)} />
    </Shell>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-[0.15em] opacity-50">{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full px-3 py-2 rounded-lg bg-black/45 border border-white/10 outline-none focus:border-amber-400/60 transition"
      />
    </label>
  );
}

function Shell({ children, onBrowse }: { children: React.ReactNode; onBrowse: () => void }) {
  return (
    <div className="min-h-[100dvh] grid place-items-center px-4 py-10 relative overflow-hidden">
      <CardFan />
      <div className="relative w-full max-w-md">
        <h1
          className="font-display text-center text-[13vw] sm:text-5xl font-black leading-none mb-1"
          style={{
            background: "linear-gradient(#ffe9b0, #e0a52c 55%, #8f5f12)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: "0.1em",
          }}
        >
          RED RISING
        </h1>
        <p className="text-center text-[10px] uppercase tracking-[0.42em] opacity-55 mb-8">
          Rise from the ashes
        </p>
        <div
          className="rounded-2xl p-6 sm:p-8"
          style={{
            background: "rgba(10,6,7,.72)",
            backdropFilter: "blur(10px)",
            boxShadow: "inset 0 0 0 1px rgba(232,188,85,.16), 0 24px 60px rgba(0,0,0,.6)",
          }}
        >
          {children}
        </div>
        <button
          onClick={onBrowse}
          className="mx-auto mt-5 block text-[11px] uppercase tracking-[0.2em] opacity-40 hover:opacity-80 transition"
        >
          Browse the 112 cards
        </button>
      </div>
    </div>
  );
}

// A slow drift of portraits behind the panel — the deck breathing under the felt.
// Plain CSS rather than a motion component: it is decoration that must never
// compete with the board for the animation budget, and a transform that is
// declared once cannot get half-applied.
function CardFan() {
  const picks = useMemo(() => {
    const all = allCards();
    if (!all.length) return [];
    // Stable across renders without randomness: walk the sorted deck at a stride
    // that lands on a spread of castes.
    const sorted = [...all].sort((a, b) => a.id.localeCompare(b.id));
    return Array.from({ length: 7 }, (_, i) => sorted[(i * 17 + 3) % sorted.length]);
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
      {picks.map((c, i) => {
        const spread = i - (picks.length - 1) / 2;
        return (
          <div
            key={c.id}
            className="card-fan absolute left-1/2 top-1/2 rounded-xl overflow-hidden"
            style={{
              width: 190,
              height: 266,
              marginLeft: -95,
              marginTop: -133,
              filter: "blur(1.5px)",
              opacity: 0.42,
              // One transform, declared once: fan out, tilt, and sag at the ends.
              transform: `translateX(${spread * 172}px) translateY(${Math.abs(spread) * 22}px) rotate(${spread * 9}deg)`,
              animationDelay: `${i * 0.9}s`,
              animationDuration: `${11 + i}s`,
            }}
          >
            <img src={portrait(c.id)} alt="" className="w-full h-[70%] object-cover" />
            <div className="h-[30%]" style={{ background: casteGradient(c.color) }} />
          </div>
        );
      })}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(48% 42% at 50% 52%, rgba(10,5,7,.92) 0%, rgba(10,5,7,.6) 60%, rgba(10,5,7,.88) 100%)",
        }}
      />
    </div>
  );
}
