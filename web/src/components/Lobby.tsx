import { useState } from "react";
import { saveCreds } from "../store";

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

  if (created) {
    const p1 = created.seats[1];
    const link = `${location.origin}/g/${created.game_id}?seat=p1&token=${encodeURIComponent(p1.token)}`;
    return (
      <Shell>
        <h1 className="text-3xl font-bold mb-2">Game created</h1>
        <p className="opacity-70 mb-4">Send this private link to {p1.name}. Then enter the table.</p>
        <div className="flex gap-2 mb-4">
          <input readOnly value={link} className="flex-1 px-3 py-2 rounded bg-black/40 border border-white/10 text-sm" />
          <button
            onClick={() => navigator.clipboard.writeText(link)}
            className="px-3 py-2 rounded bg-white/10 hover:bg-white/20 text-sm"
          >
            Copy
          </button>
        </div>
        <a
          href={`/g/${created.game_id}`}
          className="inline-block px-4 py-2 rounded bg-amber-500 hover:bg-amber-400 text-black font-medium"
        >
          Enter the table →
        </a>
      </Shell>
    );
  }

  return (
    <Shell>
      <h1 className="text-3xl font-bold mb-1">RED RISING</h1>
      <p className="opacity-70 mb-6">A two-player game for you and your partner.</p>
      <div className="space-y-3">
        <Field label="Your name" value={you} onChange={setYou} placeholder="You" />
        <Field label="Partner's name" value={partner} onChange={setPartner} placeholder="Partner" />
        <button
          onClick={create}
          disabled={busy}
          className="w-full px-4 py-2 rounded bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-semibold"
        >
          {busy ? "Creating…" : "Create game"}
        </button>
      </div>
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
      <span className="text-sm opacity-70">{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full px-3 py-2 rounded bg-black/40 border border-white/10"
      />
    </label>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-black/30 p-8">{children}</div>
    </div>
  );
}
