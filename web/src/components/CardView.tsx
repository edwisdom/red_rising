import { memo } from "react";
import { getCard } from "../cards";
import { caste, casteGradient, portrait } from "../theme";
import { Icon } from "./Icons";
import { RichText } from "./RichText";

export type CardSize = "xs" | "sm" | "md" | "lg" | "xl";

// Printed cards are poker-sized; keeping the ratio is most of what makes a
// rendered card feel like a real one.
export const CARD_RATIO = 1.4;
export const CARD_W: Record<CardSize, number> = { xs: 76, sm: 98, md: 124, lg: 172, xl: 300 };

interface Props {
  cardId: string | null; // null => hidden / face down
  faceDown?: boolean;
  size?: CardSize;
  width?: number; // overrides `size`
  selectable?: boolean;
  onClick?: () => void;
  onInspect?: (cardId: string) => void;
  /** Rendered as the sliver peeking out from under the card above it. */
  strip?: boolean;
  dim?: boolean;
}

// The sliver of a covered card that stays visible in a stack, as a fraction of
// card width. Enough for the value, the portrait and the name.
const STRIP_EM = 3.1;

export function cardHeight(size: CardSize = "md"): number {
  return Math.round(CARD_W[size] * CARD_RATIO);
}

export const CardView = memo(function CardView({
  cardId,
  faceDown,
  size = "md",
  width,
  selectable,
  onClick,
  onInspect,
  strip,
  dim,
}: Props) {
  const w = width ?? CARD_W[size];
  // One root font-size drives every internal dimension, so a card is fully
  // described by its width and stays crisp at any scale.
  const fs = w / 14;
  const h = strip ? fs * STRIP_EM : w * CARD_RATIO;

  const hidden = !cardId || faceDown;
  const card = hidden ? null : getCard(cardId!);
  const c = caste(card?.color ?? "");

  const shell: React.CSSProperties = {
    width: w,
    height: h,
    fontSize: fs,
    flexShrink: 0,
    opacity: dim ? 0.45 : 1,
  };

  if (hidden) {
    return (
      <div
        className="card overflow-hidden"
        style={{
          ...shell,
          borderRadius: strip ? "0.55em 0.55em 0 0" : undefined,
          background:
            "radial-gradient(circle at 50% 35%, #52202a 0%, #2b1116 55%, #190a0d 100%)",
          boxShadow: "inset 0 0 0 0.09em rgba(232,188,85,.28), 0 0.5em 1em rgba(0,0,0,.55)",
        }}
        title="Face-down card"
      >
        <div
          className="w-full h-full grid place-items-center"
          style={{
            backgroundImage:
              "repeating-linear-gradient(45deg, rgba(232,188,85,.05) 0 0.2em, transparent 0.2em 0.55em)",
          }}
        >
          {!strip && (
            <Icon name="EndGame" size="2.6em" style={{ color: "rgba(232,188,85,.34)" }} />
          )}
        </div>
      </div>
    );
  }

  if (!card) return <div style={shell} className="rounded-lg bg-black/40" />;

  const cls = `card overflow-hidden ${selectable ? "card-selectable" : ""} ${
    onClick || onInspect ? "card-lift" : ""
  }`;
  const frame: React.CSSProperties = {
    ...shell,
    borderRadius: strip ? "0.55em 0.55em 0 0" : "0.55em",
    background: "linear-gradient(#191216, #0e090b)",
    boxShadow: selectable
      ? undefined
      : `inset 0 0 0 0.085em ${c.base}55, inset 0 0 0.9em rgba(0,0,0,.7), 0 0.5em 1.1em rgba(0,0,0,.5)`,
  };
  const activate = onClick ?? (onInspect ? () => onInspect(card.id) : undefined);

  // In a stack only the top band shows: the value gem, a portrait chip and the
  // name — the same three things you read off the physical overlap.
  if (strip) {
    return (
      <div
        className={cls}
        style={{ ...frame, background: casteGradient(card.color), color: c.ink }}
        onClick={activate}
        onContextMenu={onInspect ? (e) => (e.preventDefault(), onInspect(card.id)) : undefined}
        title={card.name}
      >
        <div className="flex items-center h-full gap-[0.4em] px-[0.45em]">
          <Gem value={card.core_value} c={c} em={2.1} />
          <img
            src={portrait(card.id)}
            alt=""
            loading="lazy"
            className="rounded-[0.2em] object-cover"
            style={{ width: "2.05em", height: "2.05em", boxShadow: "0 0 0 0.07em rgba(0,0,0,.35)" }}
          />
          <span
            className="truncate font-bold uppercase leading-none"
            style={{ fontSize: "1.02em", letterSpacing: "0.01em" }}
          >
            {card.name}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cls}
      style={frame}
      onClick={activate}
      onContextMenu={onInspect ? (e) => (e.preventDefault(), onInspect(card.id)) : undefined}
      title={card.deploy?.text ?? card.name}
    >
      <div className="flex flex-col h-full">
        {/* Portrait, with the caste bleeding in from the edges the way the
            printed frame does. */}
        <div className="relative shrink-0" style={{ height: "8.1em" }}>
          <img
            src={portrait(card.id)}
            alt={card.name}
            loading="lazy"
            className="w-full h-full object-cover"
            style={{ objectPosition: "50% 22%" }}
          />
          <div
            className="absolute inset-0"
            style={{
              boxShadow: `inset 0 0 1.1em 0.35em ${c.shade}bb`,
              background: `linear-gradient(to bottom, transparent 55%, ${c.shade}44 100%)`,
            }}
          />
          <div className="absolute left-[0.35em] top-[0.35em]">
            <Gem value={card.core_value} c={c} em={2.9} raised />
          </div>
        </div>

        {/* Name banner — the caste gradient, embossed. */}
        <div
          className="shrink-0 flex items-baseline justify-between gap-[0.3em] px-[0.5em]"
          style={{
            background: casteGradient(card.color),
            color: c.ink,
            height: "2.15em",
            boxShadow: "inset 0 0.08em 0 rgba(255,255,255,.25), inset 0 -0.08em 0.3em rgba(0,0,0,.35)",
            alignContent: "center",
          }}
        >
          <span
            className="truncate font-bold uppercase leading-none self-center"
            style={{ fontSize: "1.05em", letterSpacing: "0.005em" }}
          >
            {card.name}
          </span>
          <span
            className="uppercase font-semibold leading-none self-center opacity-70 shrink-0"
            style={{ fontSize: "0.66em", letterSpacing: "0.08em" }}
          >
            {card.color}
          </span>
        </div>

        {/* Ability block. Anything that overruns fades out — the inspector has
            the full text one click away. */}
        <div className="relative flex-1 min-h-0">
          <div
            className="h-full overflow-hidden px-[0.5em] pt-[0.4em] leading-[1.16]"
            style={{ fontSize: "0.78em" }}
          >
            {card.deploy && (
              <p className="mb-[0.35em] text-[#e9dfda]">
                <Icon
                  name="Deploy"
                  size="0.85em"
                  style={{ color: "#e8bc55", marginRight: "0.3em" }}
                />
                <RichText raw={card.deploy.raw} refs={card.deploy.refs} />
              </p>
            )}
            {card.block && (
              <p className="mb-[0.35em] text-[#cfe6ff]">
                <Icon name="Block" size="0.85em" style={{ marginRight: "0.3em" }} />
                <RichText raw={card.block.raw} refs={card.block.refs} />
              </p>
            )}
            {card.endgame && (
              <p className="mb-[0.35em] text-[#d9c7ea]">
                <Icon name="EndGame" size="0.8em" style={{ marginRight: "0.3em" }} />
                <RichText raw={card.endgame.raw} refs={card.endgame.refs} />
              </p>
            )}
            {card.bonuses.map((b, i) => (
              <p key={i} className="text-[#cdbfb8]">
                <Points n={b.points} />
                <RichText raw={stripPoints(b.raw)} refs={b.refs} />
              </p>
            ))}
          </div>
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0"
            style={{ height: "1.5em", background: "linear-gradient(transparent, #0e090b)" }}
          />
        </div>
      </div>
    </div>
  );
});

// The core value, set in the caste's own metal.
function Gem({
  value,
  c,
  em,
  raised,
}: {
  value: number;
  c: ReturnType<typeof caste>;
  em: number;
  raised?: boolean;
}) {
  return (
    <span
      className="grid place-items-center rounded-full font-bold tabular-nums"
      style={{
        width: `${em}em`,
        height: `${em}em`,
        fontSize: "1em",
        background: `radial-gradient(circle at 32% 28%, ${c.base}, ${c.shade})`,
        color: c.ink,
        boxShadow: raised
          ? `inset 0 0.09em 0.1em rgba(255,255,255,.45), inset 0 -0.09em 0.14em rgba(0,0,0,.4), 0 0.12em 0.3em rgba(0,0,0,.65), 0 0 0 0.1em rgba(0,0,0,.35)`
          : `inset 0 0.07em 0.08em rgba(255,255,255,.4), 0 0.06em 0.14em rgba(0,0,0,.45)`,
        lineHeight: 1,
      }}
    >
      <span style={{ fontSize: `${em * 0.46}em` }}>{value}</span>
    </span>
  );
}

// Bonus points, in the game's own sign convention (U+2212 for negatives).
function Points({ n }: { n: number | null }) {
  if (n === null) return <span className="font-bold text-amber-300">? </span>;
  return (
    <span className={`font-bold ${n < 0 ? "text-red-400" : "text-amber-300"}`}>
      {n < 0 ? `−${Math.abs(n)}` : n}{" "}
    </span>
  );
}

// The raw clause repeats its own point value ("20: if with …"); the Points chip
// already shows it.
function stripPoints(raw: string): string {
  return raw.replace(/^[−-]?\d+\s*:\s*/, "");
}
