"""`Ctx`: the API every script is written against.

The turn flow (and, from Phase 3, every card ability) is a generator that talks to
the game only through a `Ctx`. Two kinds of members:

* **Mechanical ops** (plain methods) mutate a zone or resource and emit an event.
  They never ask a player anything.
* **Decision builders** (`choose_*`) return a `DecisionRequest` for the script to
  `yield`. The engine resolves the player's answer and sends back the chosen
  `Option` (or `None` when an optional decision is skipped, or a tuple for
  multi-select).

Ops that *might* need a decision are written as generators in `rules.py` and
invoked with `yield from`; they are not methods here, because only the pump can
drive a decision to completion.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from red_rising.carddefs import CardDef, load_cards
from red_rising.enums import (
    HELIUM_POINTS,  # noqa: F401  (re-exported for scripts' convenience)
    Color,
    DieFace,
    Location,
)

from .decisions import DecisionRequest, Option
from .events import (
    Banished,
    CardDrawnToHand,
    CardGained,
    CardMoved,
    Deployed,
    Event,
    FleetAdvanced,
    HeliumChanged,
    InfluencePlaced,
    Placed,
    SovereignChanged,
)
from .state import GameState, PlacedCard


class Ctx:
    def __init__(
        self,
        state: GameState,
        rng,
        emit: Callable[[Event], None],
        roll: Callable[[str], DieFace],
    ) -> None:
        self.state = state
        self.rng = rng
        self._emit = emit
        self._roll = roll  # rolls the die, emits DieRolled, returns the face

    # -- convenience read-through to state --

    @property
    def players(self):
        return self.state.players

    def opponents(self, seat: str):
        return self.state.opponents(seat)

    def hand_of(self, seat: str) -> list[str]:
        return self.state.player(seat).hand

    def neighbor_right(self, seat: str) -> str:
        """The player clockwise (to the right) of `seat`. In 2-player, the opponent."""
        players = self.state.players
        idx = next(i for i, p in enumerate(players) if p.seat == seat)
        return players[(idx + 1) % len(players)].seat

    # -- card definition lookups --

    def card(self, card_id: str) -> CardDef:
        return load_cards()[card_id]

    def color(self, card_id: str) -> Color:
        return load_cards()[card_id].color

    def is_gold(self, card_id: str) -> bool:
        return load_cards()[card_id].is_gold

    def count_in_hand(self, seat: str, *colors: Color, exclude: str | None = None) -> int:
        cards = load_cards()
        return sum(
            1
            for cid in self.state.player(seat).hand
            if cid != exclude and cards[cid].color in colors
        )

    # ---- decision builders (script yields these) ----

    def choose(
        self,
        seat: str,
        prompt: str,
        options: Iterable[Option],
        *,
        optional: bool = False,
        kind: str = "choose",
    ) -> DecisionRequest:
        opts = tuple(options)
        return DecisionRequest(
            seat=seat,
            prompt=prompt,
            options=opts,
            min_choices=0 if optional else 1,
            max_choices=1,
            kind=kind,
        )

    def choose_location(
        self,
        seat: str,
        prompt: str,
        locations: Iterable[Location],
        *,
        optional: bool = False,
        kind: str = "location",
    ) -> DecisionRequest:
        return self.choose(
            seat,
            prompt,
            [Option.of_location(loc) for loc in locations],
            optional=optional,
            kind=kind,
        )

    def choose_card(
        self,
        seat: str,
        prompt: str,
        card_ids: Iterable[str],
        *,
        optional: bool = False,
        kind: str = "card",
    ) -> DecisionRequest:
        return self.choose(
            seat,
            prompt,
            [Option.of_card(cid) for cid in card_ids],
            optional=optional,
            kind=kind,
        )

    def choose_opponent(self, seat: str, prompt: str, *, optional: bool = False) -> DecisionRequest:
        return self.choose(
            seat,
            prompt,
            [Option.of_seat(o.seat, o.name) for o in self.opponents(seat)],
            optional=optional,
            kind="opponent",
        )

    # ---- mechanical ops (no decisions) ----

    def deploy_from_hand(self, seat: str, card_id: str, loc: Location) -> None:
        player = self.state.player(seat)
        player.hand.remove(card_id)
        self.state.location(loc).place_on_top(card_id)
        self._emit(Deployed(seat=seat, card_id=card_id, location=loc))

    def place_on_location(
        self, seat: str, card_id: str, loc: Location, *, face_down: bool = False
    ) -> None:
        self.state.location(loc).place_on_top(card_id, face_down=face_down)
        self._emit(Placed(seat=seat, card_id=card_id, location=loc, face_down=face_down))

    def gain_location_top_to_hand(self, seat: str, loc: Location) -> str | None:
        stack = self.state.location(loc)
        if stack.is_empty:
            return None
        card_id = stack.take_top()
        self.state.player(seat).hand.append(card_id)
        self._emit(CardGained(seat=seat, card_id=card_id, source="location", location=loc))
        return card_id

    def gain_deck_top_to_hand(self, seat: str) -> str | None:
        card_id = self.state.draw_from_deck()
        if card_id is None:
            return None
        self.state.player(seat).hand.append(card_id)
        self._emit(CardDrawnToHand(seat=seat, card_id=card_id, source="deck"))
        self._emit(CardGained(seat=seat, card_id=card_id, source="deck"))
        return card_id

    def banish_location_top(self, loc: Location) -> str | None:
        stack = self.state.location(loc)
        if stack.is_empty:
            return None
        card_id = stack.take_top()
        self.state.banished.append(card_id)
        self._emit(Banished(card_id=card_id, source=f"location:{loc.value}"))
        return card_id

    def banish_from_hand(self, seat: str, card_id: str) -> None:
        self.state.player(seat).hand.remove(card_id)
        self.state.banished.append(card_id)
        self._emit(Banished(card_id=card_id, source=f"hand:{seat}"))

    # -- generalised zone ops used by card abilities --

    def move_card(
        self,
        card_id: str,
        to_loc: Location,
        *,
        under: str | None = None,
        face_down: bool = False,
    ) -> bool:
        """Move a card that is on some location to `to_loc` (top, or under `under`).

        Returns False if the card isn't on a location. Ability moves do NOT grant a
        location bonus (rulebook: bonuses come only from Lead/Scout).
        """
        from_loc = self.state.location_of(card_id)
        if from_loc is None:
            return False
        placed = self.state.location(from_loc).remove(card_id)
        assert placed is not None
        placed = placed.model_copy(update={"face_down": face_down})
        dest = self.state.location(to_loc)
        if under is not None and dest.insert_under(under, placed.card_id, face_down=face_down):
            pass
        else:
            dest.cards.append(placed)
        self._emit(CardMoved(card_id=card_id, from_location=from_loc, to_location=to_loc))
        return True

    def gain_card_from_location(self, seat: str, card_id: str) -> bool:
        """Gain a specific card (any position) from its location into hand. No bonus."""
        loc = self.state.location_of(card_id)
        if loc is None:
            return False
        self.state.location(loc).remove(card_id)
        self.state.player(seat).hand.append(card_id)
        self._emit(CardGained(seat=seat, card_id=card_id, source="location", location=loc))
        return True

    def regain_to_hand(self, seat: str, card_id: str) -> bool:
        """Return a card from its location to the player's hand (e.g. 'regain Alfrun')."""
        return self.gain_card_from_location(seat, card_id)

    def give_location_card_to_hand(self, card_id: str, to_seat: str) -> bool:
        """Hand a card that's on a location to another player (e.g. 'give them the Reporter')."""
        loc = self.state.location_of(card_id)
        if loc is None:
            return False
        self.state.location(loc).remove(card_id)
        self.state.player(to_seat).hand.append(card_id)
        self._emit(CardGained(seat=to_seat, card_id=card_id, source="location", location=loc))
        return True

    def place_banished_at_bottom(self, seat: str, card_id: str, loc: Location) -> bool:
        """Move a banished card to the bottom of a location's stack (Researcher)."""
        if card_id not in self.state.banished:
            return False
        self.state.banished.remove(card_id)
        self.state.location(loc).cards.insert(0, PlacedCard(card_id=card_id))
        self._emit(Placed(seat=seat, card_id=card_id, location=loc))
        return True

    def place_under(
        self, seat: str, card_id: str, target: str, loc: Location, *, face_down: bool = False
    ) -> None:
        """Insert a loose card (e.g. revealed from the deck) directly under `target`."""
        stack = self.state.location(loc)
        if not stack.insert_under(target, card_id, face_down=face_down):
            stack.cards.insert(0, PlacedCard(card_id=card_id, face_down=face_down))
        self._emit(Placed(seat=seat, card_id=card_id, location=loc))

    def take_banished(self, card_id: str) -> bool:
        if card_id in self.state.banished:
            self.state.banished.remove(card_id)
            return True
        return False

    def put_on_deck(self, card_id: str, *, top: bool = True) -> None:
        """Return a loose card to the deck (top is the last element)."""
        if top:
            self.state.deck.append(card_id)
        else:
            self.state.deck.insert(0, card_id)

    def banish_card(self, card_id: str) -> bool:
        """Banish a specific card from wherever it is (location or hand)."""
        loc = self.state.location_of(card_id)
        if loc is not None:
            self.state.location(loc).remove(card_id)
            self.state.banished.append(card_id)
            self._emit(Banished(card_id=card_id, source=f"location:{loc.value}"))
            return True
        for p in self.state.players:
            if card_id in p.hand:
                p.hand.remove(card_id)
                self.state.banished.append(card_id)
                self._emit(Banished(card_id=card_id, source=f"hand:{p.seat}"))
                return True
        return False

    # -- deck ops --

    def reveal_deck_top(self) -> str | None:
        """Pop the top card of the deck (caller decides where it goes)."""
        return self.state.draw_from_deck()

    def take_deck_bottom(self) -> str | None:
        return self.state.deck.pop(0) if self.state.deck else None

    def peek_deck_bottom(self) -> str | None:
        return self.state.deck[0] if self.state.deck else None

    def card_to_hand(self, seat: str, card_id: str, *, source: str = "deck") -> None:
        """Put an already-removed card (e.g. a revealed deck card) into a hand."""
        self.state.player(seat).hand.append(card_id)
        self._emit(CardGained(seat=seat, card_id=card_id, source="deck"))
        _ = source

    def gain_banished(self, seat: str, card_id: str) -> bool:
        if card_id not in self.state.banished:
            return False
        self.state.banished.remove(card_id)
        self.state.player(seat).hand.append(card_id)
        self._emit(CardGained(seat=seat, card_id=card_id, source="location"))
        return True

    def banish_deck_card(self, seat: str, card_id: str) -> None:
        """Banish a card already removed from the deck."""
        self.state.banished.append(card_id)
        self._emit(Banished(card_id=card_id, source="deck"))
        _ = seat

    # -- resources --

    def gain_helium(self, seat: str, n: int = 1) -> None:
        total = self.state.player(seat).gain_helium(n)
        self._emit(HeliumChanged(seat=seat, delta=n, total=total))

    def lose_helium(self, seat: str, n: int = 1) -> None:
        p = self.state.player(seat)
        before = p.helium
        total = p.lose_helium(n)
        self._emit(HeliumChanged(seat=seat, delta=total - before, total=total))

    def advance_fleet(self, seat: str, n: int = 1) -> None:
        to = self.state.player(seat).advance_fleet(n)
        self._emit(FleetAdvanced(seat=seat, to=to))

    def place_influence(self, seat: str, n: int = 1) -> None:
        placed = self.state.player(seat).place_influence(n)
        if placed:
            self._emit(
                InfluencePlaced(
                    seat=seat,
                    count=placed,
                    on_institute=self.state.player(seat).influence_on_institute,
                )
            )

    def remove_influence(self, seat: str, n: int = 1) -> int:
        """Return up to `n` Institute influence tokens to the player's supply."""
        p = self.state.player(seat)
        moved = min(n, p.influence_on_institute)
        p.influence_on_institute -= moved
        p.influence_supply += moved
        if moved:
            self._emit(
                InfluencePlaced(seat=seat, count=-moved, on_institute=p.influence_on_institute)
            )
        return moved

    def regress_fleet(self, seat: str, n: int = 1) -> None:
        p = self.state.player(seat)
        p.fleet = max(0, p.fleet - n)
        self._emit(FleetAdvanced(seat=seat, to=p.fleet))

    def set_sovereign(self, seat: str) -> bool:
        """Give the Sovereign token to `seat`. Returns True if the holder changed."""
        prev = self.state.sovereign_holder
        self.state.sovereign_holder = seat
        for p in self.state.players:
            p.has_sovereign = p.seat == seat
        self._emit(SovereignChanged(seat=seat, from_seat=prev))
        return prev != seat

    def roll_die(self, seat: str) -> DieFace:
        """Roll the Rising die. The outcome is recorded as a DieRolled event."""
        return self._roll(seat)
