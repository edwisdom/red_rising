"""Per-viewer redaction: `redact(state, viewer) -> PlayerView`.

The server holds full state; each client sees only what a player at the table
could. Getting this wrong leaks your partner's hand and silently ruins the game,
so it lives in one small, heavily tested function.

Card *visuals* (name, color, core value, ability text) are NOT sent here — the
client already has `cards.json`. The view sends card **ids** and positions; unknown
cards are sent as counts or nulls.

What is hidden from a viewer:
* opponents' hands — only a count;
* the deck — only a count, never its order;
* face-down location cards (Firewall Expert) — id nulled for everyone until
  revealed (they count as colorless anyway);
* a pending decision belongs to exactly one seat; others see only that someone is
  being waited on, never the option list.

What is public (per the rulebook): every face-up card on every location, the
banished pile, all tokens and tracks.
"""

from __future__ import annotations

from pydantic import BaseModel

from red_rising.engine.decisions import PendingDecision
from red_rising.engine.scoring import ScoreBreakdown
from red_rising.engine.state import GameState
from red_rising.enums import House, Location


class CardSlot(BaseModel):
    """One card on a location stack. `card_id` is null when hidden (face down)."""

    card_id: str | None
    face_down: bool = False


class LocationView(BaseModel):
    location: Location
    cards: list[CardSlot]


class SelfView(BaseModel):
    seat: str
    name: str
    house: House
    hand: list[str]  # your own card ids, in hand order
    helium: int
    fleet: int
    influence_on_institute: int
    influence_supply: int
    has_sovereign: bool


class OpponentView(BaseModel):
    seat: str
    name: str
    house: House
    hand_count: int  # never the ids
    helium: int
    fleet: int
    influence_on_institute: int
    influence_supply: int
    has_sovereign: bool


class WaitingOn(BaseModel):
    seat: str
    name: str
    prompt: str


class PlayerView(BaseModel):
    """Everything one seat is allowed to see. The whole client renders from this."""

    game_id: str
    seat: str
    turn_number: int
    current_player_seat: str | None
    first_player_seat: str

    you: SelfView
    opponents: list[OpponentView]
    locations: list[LocationView]
    deck_count: int
    banished: list[str]
    sovereign_holder: str | None
    neutral_influence: int

    pending: PendingDecision | None = None  # present only if it's YOUR decision
    waiting_on: WaitingOn | None = None  # present if someone else must decide

    finished: bool = False
    scores: dict[str, ScoreBreakdown] | None = None

    #: Log length at render time; a client can request events after this on resync.
    last_seq: int = 0


def redact_event(event, viewer: str) -> dict | None:
    """Redact one event for the log a `viewer` receives.

    Card ids that would leak an opponent's private draw are nulled; the internal
    `decision_made` bookkeeping event is dropped entirely.
    """
    d = event.model_dump(mode="json")
    kind = d.get("type")
    if kind == "decision_made":
        return None
    if kind in ("card_dealt", "card_drawn_to_hand") and d.get("seat") != viewer:
        d["card_id"] = None
    if kind == "card_stolen" and viewer not in (d.get("from_seat"), d.get("to_seat")):
        d["card_id"] = None
    return d


def _slot(card_id: str, face_down: bool, viewer: str, placed_by: str | None) -> CardSlot:
    # Face-down cards are hidden from everyone until revealed. (When Phase 3 adds
    # Firewall Expert, `placed_by` will let the placer keep seeing their own.)
    if face_down and viewer != placed_by:
        return CardSlot(card_id=None, face_down=True)
    return CardSlot(card_id=card_id, face_down=face_down)


def redact(
    state: GameState,
    viewer: str,
    *,
    pending: PendingDecision | None,
    last_seq: int,
    scores: dict[str, ScoreBreakdown] | None = None,
) -> PlayerView:
    me = state.player(viewer)

    you = SelfView(
        seat=me.seat,
        name=me.name,
        house=me.house,
        hand=list(me.hand),
        helium=me.helium,
        fleet=me.fleet,
        influence_on_institute=me.influence_on_institute,
        influence_supply=me.influence_supply,
        has_sovereign=me.has_sovereign,
    )
    opponents = [
        OpponentView(
            seat=o.seat,
            name=o.name,
            house=o.house,
            hand_count=len(o.hand),
            helium=o.helium,
            fleet=o.fleet,
            influence_on_institute=o.influence_on_institute,
            influence_supply=o.influence_supply,
            has_sovereign=o.has_sovereign,
        )
        for o in state.opponents(viewer)
    ]
    locations = [
        LocationView(
            location=loc,
            cards=[_slot(c.card_id, c.face_down, viewer, None) for c in state.location(loc).cards],
        )
        for loc in Location
    ]

    my_pending = pending if (pending is not None and pending.seat == viewer) else None
    waiting: WaitingOn | None = None
    if pending is not None and pending.seat != viewer:
        who = state.player(pending.seat)
        waiting = WaitingOn(seat=who.seat, name=who.name, prompt=pending.prompt)

    return PlayerView(
        game_id=state.game_id,
        seat=viewer,
        turn_number=state.turn_number,
        current_player_seat=state.players[state.current_player_index].seat,
        first_player_seat=state.players[state.first_player_index].seat,
        you=you,
        opponents=opponents,
        locations=locations,
        deck_count=len(state.deck),
        banished=list(state.banished),
        sovereign_holder=state.sovereign_holder,
        neutral_influence=state.neutral_influence,
        pending=my_pending,
        waiting_on=waiting,
        finished=state.finished,
        scores=scores,
        last_seq=last_seq,
    )
