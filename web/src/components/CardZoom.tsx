import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { getCard } from "../cards";
import { caste, casteGradient, portrait } from "../theme";
import { Icon } from "./Icons";
import { RichText } from "./RichText";

// Reading a card is the thing you do most, so it gets two speeds: hover a card
// and a full-size copy pops out beside it (no click, no commitment), or open the
// inspector to read it properly and arrow through whatever list it came from.
interface ZoomApi {
  peek: (cardId: string, from: DOMRect) => void;
  endPeek: () => void;
  inspect: (cardId: string, list?: string[]) => void;
}
const Ctx = createContext<ZoomApi | null>(null);

export function useCardZoom(): ZoomApi {
  const api = useContext(Ctx);
  if (!api) throw new Error("useCardZoom outside CardZoomProvider");
  return api;
}

const PEEK_DELAY = 260;
const PEEK_W = 250;

export function CardZoomProvider({ children }: { children: ReactNode }) {
  const [peeked, setPeeked] = useState<{ id: string; rect: DOMRect } | null>(null);
  const [modal, setModal] = useState<{ id: string; list: string[] } | null>(null);
  const timer = useRef<number | null>(null);

  const endPeek = useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = null;
    setPeeked(null);
  }, []);

  const peek = useCallback((cardId: string, from: DOMRect) => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setPeeked({ id: cardId, rect: from }), PEEK_DELAY);
  }, []);

  const inspect = useCallback(
    (cardId: string, list?: string[]) => {
      endPeek();
      setModal({ id: cardId, list: list?.length ? list : [cardId] });
    },
    [endPeek],
  );

  const api = useMemo(() => ({ peek, endPeek, inspect }), [peek, endPeek, inspect]);

  return (
    <Ctx.Provider value={api}>
      {children}
      <PeekLayer peeked={peeked} />
      <InspectorModal
        state={modal}
        onClose={() => setModal(null)}
        onNavigate={(id) => setModal((m) => (m ? { ...m, id } : m))}
      />
    </Ctx.Provider>
  );
}

/** Wrap a card to make it readable: hover peeks, click inspects. */
export function Zoomable({
  cardId,
  list,
  children,
  disabled,
  className,
}: {
  cardId: string | null;
  list?: string[];
  children: ReactNode;
  /** Set when the card is a legal choice — the click belongs to the game then. */
  disabled?: boolean;
  className?: string;
}) {
  const { peek, endPeek, inspect } = useCardZoom();
  const ref = useRef<HTMLDivElement>(null);
  if (!cardId) return <div className={className}>{children}</div>;

  const rect = () => ref.current?.getBoundingClientRect();
  return (
    <div
      ref={ref}
      className={className}
      onMouseEnter={() => {
        const r = rect();
        if (r) peek(cardId, r);
      }}
      onMouseLeave={endPeek}
      onClick={disabled ? undefined : () => inspect(cardId, list)}
      onContextMenu={(e) => {
        e.preventDefault();
        inspect(cardId, list);
      }}
    >
      {children}
    </div>
  );
}

// The hover copy, placed beside its source card and flipped to stay on screen.
function PeekLayer({ peeked }: { peeked: { id: string; rect: DOMRect } | null }) {
  if (typeof document === "undefined") return null;
  return createPortal(
    <AnimatePresence>
      {peeked && <Peek key={peeked.id + peeked.rect.top} id={peeked.id} rect={peeked.rect} />}
    </AnimatePresence>,
    document.body,
  );
}

function Peek({ id, rect }: { id: string; rect: DOMRect }) {
  const h = PEEK_W * 1.4;
  const pad = 12;
  // Prefer the right; fall back left, then clamp into the viewport.
  let left = rect.right + pad;
  if (left + PEEK_W > window.innerWidth - 8) left = rect.left - PEEK_W - pad;
  if (left < 8) left = Math.min(Math.max(8, rect.left), window.innerWidth - PEEK_W - 8);
  const top = Math.min(Math.max(8, rect.top + rect.height / 2 - h / 2), window.innerHeight - h - 8);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94, transition: { duration: 0.1 } }}
      transition={{ type: "spring", stiffness: 480, damping: 32 }}
      className="fixed z-[80] pointer-events-none"
      style={{ left, top, filter: "drop-shadow(0 1.5rem 2.5rem rgba(0,0,0,.75))" }}
    >
      <CardFull cardId={id} width={PEEK_W} />
    </motion.div>
  );
}

// The full, untruncated card. Same furniture as the table card, but the ability
// text is allowed all the room it needs.
export function CardFull({
  cardId,
  width = 300,
  onCardRef,
}: {
  cardId: string;
  width?: number;
  onCardRef?: (id: string) => void;
}) {
  const card = getCard(cardId);
  if (!card) return null;
  const c = caste(card.color);
  const fs = width / 16;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        width,
        fontSize: fs,
        background: "linear-gradient(#1a1216, #0d0809)",
        boxShadow: `inset 0 0 0 0.1em ${c.base}66, inset 0 0 1.4em rgba(0,0,0,.8)`,
      }}
    >
      <div className="relative" style={{ height: "9.6em" }}>
        <img
          src={portrait(card.id)}
          alt={card.name}
          className="w-full h-full object-cover"
          style={{ objectPosition: "50% 20%" }}
        />
        <div
          className="absolute inset-0"
          style={{
            boxShadow: `inset 0 0 1.6em 0.45em ${c.shade}cc`,
            background: `linear-gradient(to bottom, transparent 50%, ${c.shade}55 100%)`,
          }}
        />
        <div
          className="absolute left-[0.5em] top-[0.5em] grid place-items-center rounded-full font-bold tabular-nums"
          style={{
            width: "3.1em",
            height: "3.1em",
            background: `radial-gradient(circle at 32% 28%, ${c.base}, ${c.shade})`,
            color: c.ink,
            boxShadow:
              "inset 0 0.1em 0.12em rgba(255,255,255,.45), inset 0 -0.1em 0.16em rgba(0,0,0,.4), 0 0.16em 0.4em rgba(0,0,0,.7), 0 0 0 0.1em rgba(0,0,0,.4)",
          }}
        >
          <span style={{ fontSize: "1.5em", lineHeight: 1 }}>{card.core_value}</span>
        </div>
      </div>

      <div
        className="flex items-center justify-between gap-2 px-[0.7em] py-[0.35em]"
        style={{
          background: casteGradient(card.color),
          color: c.ink,
          boxShadow: "inset 0 0.1em 0 rgba(255,255,255,.28), inset 0 -0.1em 0.3em rgba(0,0,0,.35)",
        }}
      >
        <span className="font-bold uppercase leading-tight" style={{ fontSize: "1.25em" }}>
          {card.name}
        </span>
        <span
          className="uppercase font-semibold opacity-75 shrink-0"
          style={{ fontSize: "0.72em", letterSpacing: "0.1em" }}
        >
          {card.color}
        </span>
      </div>

      <div className="px-[0.75em] py-[0.6em] space-y-[0.5em]" style={{ fontSize: "0.92em" }}>
        {card.deploy && (
          <Clause icon="Deploy" tint="#e8bc55" label="Deploy">
            <RichText raw={card.deploy.raw} refs={card.deploy.refs} onCardRef={onCardRef} />
          </Clause>
        )}
        {card.block && (
          <Clause icon="Block" tint="#7fc4ff" label="Block">
            <RichText raw={card.block.raw} refs={card.block.refs} onCardRef={onCardRef} />
          </Clause>
        )}
        {card.endgame && (
          <Clause icon="EndGame" tint="#c9a4e8" label="End of game">
            <RichText raw={card.endgame.raw} refs={card.endgame.refs} onCardRef={onCardRef} />
          </Clause>
        )}
        {card.bonuses.length > 0 && (
          <div className="pt-[0.35em] border-t border-white/10 space-y-[0.3em]">
            {card.bonuses.map((b, i) => (
              <div key={i} className="flex gap-[0.5em] leading-snug">
                <span
                  className={`font-bold tabular-nums shrink-0 ${
                    (b.points ?? 0) < 0 ? "text-red-400" : "text-amber-300"
                  }`}
                  style={{ minWidth: "2.2em", textAlign: "right" }}
                >
                  {b.points === null ? "?" : b.points < 0 ? `−${Math.abs(b.points)}` : b.points}
                </span>
                <span className="text-[#d5c8c1]">
                  <RichText raw={b.raw.replace(/^[−-]?\d+\s*:\s*/, "")} refs={b.refs} onCardRef={onCardRef} />
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Clause({
  icon,
  tint,
  label,
  children,
}: {
  icon: "Deploy" | "Block" | "EndGame";
  tint: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex gap-[0.5em] leading-snug">
      <span
        className="shrink-0 grid place-items-center rounded"
        style={{ width: "1.5em", height: "1.5em", color: tint, background: `${tint}1a` }}
        title={label}
      >
        <Icon name={icon} size="0.95em" />
      </span>
      <span className="text-[#e6dcd6] pt-[0.1em]">{children}</span>
    </div>
  );
}

// The inspector: one card, big, with arrows through the list it came from.
function InspectorModal({
  state,
  onClose,
  onNavigate,
}: {
  state: { id: string; list: string[] } | null;
  onClose: () => void;
  onNavigate: (id: string) => void;
}) {
  const list = state?.list ?? [];
  const idx = state ? list.indexOf(state.id) : -1;

  useEffect(() => {
    if (!state) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && idx > 0) onNavigate(list[idx - 1]);
      if (e.key === "ArrowRight" && idx >= 0 && idx < list.length - 1) onNavigate(list[idx + 1]);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, idx, list, onClose, onNavigate]);

  if (typeof document === "undefined") return null;
  return createPortal(
    <AnimatePresence>
      {state && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[90] grid place-items-center bg-black/70 backdrop-blur-sm px-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.92, y: 18 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            className="flex items-center gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <NavBtn
              dir="◀"
              disabled={idx <= 0}
              onClick={() => onNavigate(list[idx - 1])}
              label="Previous card"
            />
            <div>
              <CardFull
                cardId={state.id}
                width={Math.min(340, typeof window !== "undefined" ? window.innerWidth - 130 : 340)}
                onCardRef={(id) => onNavigate(id)}
              />
              {list.length > 1 && (
                <div className="text-center text-xs opacity-50 mt-2 tabular-nums">
                  {idx + 1} / {list.length} · ← → to browse · Esc to close
                </div>
              )}
            </div>
            <NavBtn
              dir="▶"
              disabled={idx < 0 || idx >= list.length - 1}
              onClick={() => onNavigate(list[idx + 1])}
              label="Next card"
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

function NavBtn({
  dir,
  disabled,
  onClick,
  label,
}: {
  dir: string;
  disabled: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="w-10 h-16 shrink-0 rounded-lg bg-white/5 hover:bg-white/15 disabled:opacity-0 disabled:pointer-events-none text-amber-200 text-lg transition"
    >
      {dir}
    </button>
  );
}
