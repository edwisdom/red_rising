"""Mutable game state and its zones.

A card in play is identified by its `id` alone — all 112 ids are unique, so we
never need per-instance objects. Every card sits in exactly one zone at all times
(deck, a location stack, a hand, or the banished pile); `all_card_ids()` and the
conservation test in `tests/` enforce that.

State is deliberately mutable and JSON-serialisable. The engine mutates it in
place and snapshots it (deep copy) at turn boundaries.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from red_rising.carddefs import load_cards
from red_rising.enums import (
    MAX_FLEET,
    MAX_INFLUENCE,
    House,
    Location,
)


class PlacedCard(BaseModel):
    """One card on a location stack.

    `face_down` cards (from Firewall Expert) are hidden from opponents and count
    as colorless for scoring until revealed. The flag exists from Phase 1 so the
    zone shape never has to change; nothing sets it until Phase 3.
    """

    card_id: str
    face_down: bool = False


class LocationStack(BaseModel):
    """An ordered pile at a location. The top card is the last element."""

    location: Location
    cards: list[PlacedCard] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.cards

    def top(self) -> PlacedCard | None:
        return self.cards[-1] if self.cards else None

    def place_on_top(self, card_id: str, *, face_down: bool = False) -> None:
        self.cards.append(PlacedCard(card_id=card_id, face_down=face_down))

    def take_top(self) -> str:
        return self.cards.pop().card_id

    def bottom(self) -> PlacedCard | None:
        return self.cards[0] if self.cards else None

    def card_ids(self) -> list[str]:
        return [c.card_id for c in self.cards]

    def index_of(self, card_id: str) -> int | None:
        for i, c in enumerate(self.cards):
            if c.card_id == card_id:
                return i
        return None

    def below(self, card_id: str) -> str | None:
        """The card directly under `card_id` in this stack (None if it's the bottom)."""
        i = self.index_of(card_id)
        if i is None or i == 0:
            return None
        return self.cards[i - 1].card_id

    def remove(self, card_id: str) -> PlacedCard | None:
        i = self.index_of(card_id)
        if i is None:
            return None
        return self.cards.pop(i)

    def insert_under(self, target: str, card_id: str, *, face_down: bool = False) -> bool:
        """Insert `card_id` directly beneath `target`. Returns False if target absent."""
        i = self.index_of(target)
        if i is None:
            return False
        self.cards.insert(i, PlacedCard(card_id=card_id, face_down=face_down))
        return True


class PlayerState(BaseModel):
    seat: str  # stable per-game id, e.g. "p0"; also the per-seat auth subject
    name: str
    house: House

    hand: list[str] = Field(default_factory=list)  # card ids, private to this seat
    helium: int = 0
    fleet: int = 0  # position on the Fleet Track, 0..MAX_FLEET
    influence_supply: int = MAX_INFLUENCE  # tokens not yet placed
    influence_on_institute: int = 0
    has_sovereign: bool = False
    #: Direct points from end-of-game (⏰) abilities like Hacker; added at scoring.
    endgame_points: int = 0

    # --- guarded mutators: keep the rulebook's caps in one place ---

    def gain_helium(self, n: int = 1) -> int:
        self.helium += n
        return self.helium

    def lose_helium(self, n: int = 1) -> int:
        self.helium = max(0, self.helium - n)
        return self.helium

    def advance_fleet(self, n: int = 1) -> int:
        self.fleet = min(MAX_FLEET, self.fleet + n)
        return self.fleet

    def place_influence(self, n: int = 1) -> int:
        """Move up to `n` tokens from supply onto the Institute. Returns count placed."""
        moved = min(n, self.influence_supply)
        self.influence_supply -= moved
        self.influence_on_institute += moved
        return moved


class GameState(BaseModel):
    game_id: str
    seed: int

    players: list[PlayerState]
    deck: list[str] = Field(default_factory=list)  # top of deck is the last element
    locations: dict[Location, LocationStack] = Field(default_factory=dict)
    banished: list[str] = Field(default_factory=list)  # face up, unordered

    sovereign_holder: str | None = None  # seat id, or None if with no one
    neutral_influence: int = 0  # 2-player neutral house tokens on the Institute

    first_player_index: int = 0
    current_player_index: int = 0
    turn_number: int = 0  # 1-based count of turns begun (0 before play starts)
    #: 0-based index of the turn that first met the end condition (None until then).
    end_triggered_on_turn: int | None = None
    apollo_bonus_taken: bool = False  # Apollo's one extra final turn
    finished: bool = False

    # --- deck helpers (top = last element) ---

    def draw_from_deck(self) -> str | None:
        return self.deck.pop() if self.deck else None

    def peek_deck_top(self) -> str | None:
        return self.deck[-1] if self.deck else None

    # --- lookups ---

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def player(self, seat: str) -> PlayerState:
        for p in self.players:
            if p.seat == seat:
                return p
        raise KeyError(seat)

    def opponents(self, seat: str) -> list[PlayerState]:
        return [p for p in self.players if p.seat != seat]

    def location(self, loc: Location) -> LocationStack:
        return self.locations[loc]

    def location_of(self, card_id: str) -> Location | None:
        """Which location's stack currently holds `card_id` (None if not on a location)."""
        for loc, stack in self.locations.items():
            if stack.index_of(card_id) is not None:
                return loc
        return None

    # --- invariant support ---

    def all_card_ids(self) -> list[str]:
        """Every card id across every zone, WITH duplicates if any (for conservation checks)."""
        ids: list[str] = list(self.deck)
        for stack in self.locations.values():
            ids.extend(stack.card_ids())
        for p in self.players:
            ids.extend(p.hand)
        ids.extend(self.banished)
        return ids

    def assert_card_conservation(self) -> None:
        """Every one of the 112 cards is in exactly one zone. The load-bearing invariant."""
        ids = self.all_card_ids()
        expected = set(load_cards().by_id)
        seen = set(ids)
        if len(ids) != len(expected) or seen != expected:
            missing = expected - seen
            extra = [i for i in ids if ids.count(i) > 1]
            raise AssertionError(
                f"card conservation violated: {len(ids)} ids, "
                f"missing={sorted(missing)}, duplicated={sorted(set(extra))}"
            )
