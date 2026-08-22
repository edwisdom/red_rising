import { Fragment, type ReactNode } from "react";
import type { Ref } from "../types";
import { caste } from "../theme";
import { Icon, type IconName } from "./Icons";

// Card text ships as markdown: "[Banish](#banish) the card under this one."
// Rendering those links the way the printed card does — game icons for the
// keywords, caste-tinted names for the colors, tappable cross-references for
// other characters — is most of what makes a card readable at a glance.
const KEYWORD_ICON: Record<string, IconName> = {
  banish: "Banish",
  deploy: "Deploy",
  block: "Block",
  reveal: "Deck",
  scout: "Deck",
  deck: "Deck",
  jupiter: "Jupiter",
  mars: "Mars",
  luna: "Luna",
  institute: "Institute",
  "fleet-track": "Jupiter",
  scoring: "EndGame",
  "game-end": "EndGame",
};

const LINK_RE = /\[([^\]]+)\]\(#([^)]+)\)/g;

export function RichText({
  raw,
  refs = [],
  onCardRef,
}: {
  raw: string;
  refs?: Ref[];
  onCardRef?: (cardId: string) => void;
}) {
  const byLabel = new Map(refs.map((r) => [r.label.toLowerCase(), r]));
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;

  for (const m of raw.matchAll(LINK_RE)) {
    const [full, label, anchor] = m;
    const at = m.index!;
    if (at > last) out.push(<Fragment key={key++}>{raw.slice(last, at)}</Fragment>);
    last = at + full.length;

    const ref = byLabel.get(label.toLowerCase());
    const icon = KEYWORD_ICON[anchor];

    if (ref?.kind === "color") {
      const c = caste(ref.target);
      out.push(
        <span
          key={key++}
          className="font-semibold"
          style={{ color: c.base, textShadow: `0 0 0.5em ${c.shade}` }}
        >
          {label}
        </span>,
      );
    } else if (ref?.kind === "character") {
      out.push(
        <button
          key={key++}
          type="button"
          onClick={onCardRef ? (e) => (e.stopPropagation(), onCardRef(ref.target)) : undefined}
          className="font-semibold text-amber-200 underline decoration-amber-200/40 underline-offset-2 hover:decoration-amber-200 disabled:no-underline"
          disabled={!onCardRef}
        >
          {label}
        </button>,
      );
    } else if (icon) {
      out.push(
        <span key={key++} className="whitespace-nowrap font-semibold text-amber-100/90">
          <Icon name={icon} size="0.95em" style={{ marginRight: "0.15em" }} />
          {label}
        </span>,
      );
    } else {
      out.push(<Fragment key={key++}>{label}</Fragment>);
    }
  }
  if (last < raw.length) out.push(<Fragment key={key++}>{raw.slice(last)}</Fragment>);
  return <>{out}</>;
}
