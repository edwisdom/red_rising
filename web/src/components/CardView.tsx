import { getCard, CASTE_HEX, textOn } from "../cards";

interface Props {
  cardId: string | null; // null => face down / hidden
  faceDown?: boolean;
  size?: "sm" | "md" | "lg";
  selectable?: boolean;
  onClick?: () => void;
  covered?: boolean; // rendered peeking out from under another card
}

const SIZES = {
  sm: { w: 92, h: 128, name: 11, val: 15, body: 8.5 },
  md: { w: 120, h: 168, name: 13, val: 20, body: 10 },
  lg: { w: 150, h: 210, name: 15, val: 24, body: 11 },
};

// A data-driven card face: color band, core value, name, and ability text. No art
// assets — the CardDef carries an optional `art_url` slot for later.
export function CardView({ cardId, faceDown, size = "md", selectable, onClick, covered }: Props) {
  const s = SIZES[size];
  if (!cardId || faceDown) {
    return (
      <div
        className="card rounded-lg border border-black/40 shrink-0"
        style={{
          width: s.w,
          height: covered ? 30 : s.h,
          background: "repeating-linear-gradient(45deg,#3a1a20,#3a1a20 6px,#2c1318 6px,#2c1318 12px)",
        }}
        title="Hidden card"
      />
    );
  }

  const card = getCard(cardId);
  if (!card) return <div style={{ width: s.w, height: s.h }} className="bg-black/30 rounded-lg" />;

  const band = CASTE_HEX[card.color] ?? "#555";
  const fg = textOn(card.color);

  // When covered, only the top strip (value / name / color) shows, matching the
  // physical game's overlap.
  if (covered) {
    return (
      <div
        className={`card rounded-t-lg border-t border-x border-black/40 shrink-0 ${selectable ? "card-selectable" : ""}`}
        style={{ width: s.w, height: 30, background: band, color: fg }}
        onClick={onClick}
        title={card.name}
      >
        <div className="flex items-center gap-1 px-1.5 h-full" style={{ fontSize: s.name }}>
          <span className="font-bold" style={{ fontSize: s.val }}>
            {card.core_value}
          </span>
          <span className="truncate font-medium">{card.name}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`card rounded-lg overflow-hidden border border-black/50 shrink-0 flex flex-col ${selectable ? "card-selectable" : ""}`}
      style={{ width: s.w, height: s.h, background: "#1c1418", color: "#eee" }}
      onClick={onClick}
      title={card.deploy?.text ?? card.name}
    >
      <div
        className="flex items-center justify-between px-1.5 py-0.5"
        style={{ background: band, color: fg }}
      >
        <span className="font-extrabold leading-none" style={{ fontSize: s.val }}>
          {card.core_value}
        </span>
        <span className="uppercase tracking-wide opacity-80" style={{ fontSize: s.body }}>
          {card.color}
        </span>
      </div>
      <div className="px-1.5 pt-1 font-semibold leading-tight" style={{ fontSize: s.name }}>
        {card.name}
      </div>
      <div className="px-1.5 py-1 opacity-85 leading-snug overflow-hidden" style={{ fontSize: s.body }}>
        {card.deploy && <div className="mb-1">⚡ {card.deploy.text}</div>}
        {card.bonuses.map((b, i) => (
          <div key={i} className="opacity-90">
            🏆 {b.points === null ? "?" : b.points}: {b.condition}
          </div>
        ))}
      </div>
    </div>
  );
}
