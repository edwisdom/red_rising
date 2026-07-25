"""Events: the append-only record of everything that happens.

Every mutation, every RNG outcome, and every answered decision becomes an event.
The log is what the frontend renders ("Aja banished your Sevro"), what makes bug
reports reproducible ("game X, event 47"), and — replayed onto a snapshot — what
rebuilds a game after a restart.

Events are a discriminated union on `type`, so they serialise to and from JSON
unambiguously. They are facts about the past: never mutate one.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from red_rising.enums import DieFace, House, Location


class _Event(BaseModel):
    model_config = {"frozen": True}

    #: 0-based position in the log. Left at 0 by callers; the engine stamps the
    #: real value when it appends the event.
    seq: int = 0


class GameStarted(_Event):
    type: Literal["game_started"] = "game_started"
    seed: int
    seats: tuple[str, ...]
    houses: dict[str, House]
    first_player: str


class CardDealt(_Event):
    type: Literal["card_dealt"] = "card_dealt"
    seat: str
    card_id: str  # redacted to null for opponents at the transport layer


class CardsToLocation(_Event):
    """Setup / scout: cards placed (not deployed) onto a location."""

    type: Literal["cards_to_location"] = "cards_to_location"
    location: Location
    card_ids: tuple[str, ...]
    face_down: bool = False


class TurnBegan(_Event):
    type: Literal["turn_began"] = "turn_began"
    seat: str
    turn_number: int


class ActionChosen(_Event):
    type: Literal["action_chosen"] = "action_chosen"
    seat: str
    action: Literal["lead", "scout"]


class Deployed(_Event):
    type: Literal["deployed"] = "deployed"
    seat: str
    card_id: str
    location: Location


class Placed(_Event):
    """A single card placed (not deployed) on a location, e.g. by Scout or a die."""

    type: Literal["placed"] = "placed"
    seat: str
    card_id: str
    location: Location
    face_down: bool = False


class CardGained(_Event):
    type: Literal["card_gained"] = "card_gained"
    seat: str
    card_id: str
    source: Literal["location", "deck"]
    location: Location | None = None


class CardDrawnToHand(_Event):
    type: Literal["card_drawn_to_hand"] = "card_drawn_to_hand"
    seat: str
    card_id: str  # redacted for opponents
    source: Literal["deck", "location"]


class Banished(_Event):
    type: Literal["banished"] = "banished"
    card_id: str
    source: str  # "deck" | "location:Mars" | "hand:p0" | ...


class CardMoved(_Event):
    """A card relocated between/within locations by an ability (not a deploy)."""

    type: Literal["card_moved"] = "card_moved"
    card_id: str
    from_location: Location
    to_location: Location


class CardStolen(_Event):
    type: Literal["card_stolen"] = "card_stolen"
    from_seat: str
    to_seat: str
    card_id: str


class Blocked(_Event):
    """A player revealed a block card to prevent an opponent's steal/banish/sovereign
    theft. `kind` is 'card' or 'sovereign'."""

    type: Literal["blocked"] = "blocked"
    seat: str  # the defender who revealed the block
    block_card: str
    kind: str


class LocationBonus(_Event):
    type: Literal["location_bonus"] = "location_bonus"
    seat: str
    location: Location


class DieRolled(_Event):
    type: Literal["die_rolled"] = "die_rolled"
    seat: str
    face: DieFace


class HeliumChanged(_Event):
    type: Literal["helium_changed"] = "helium_changed"
    seat: str
    delta: int
    total: int


class FleetAdvanced(_Event):
    type: Literal["fleet_advanced"] = "fleet_advanced"
    seat: str
    to: int


class InfluencePlaced(_Event):
    type: Literal["influence_placed"] = "influence_placed"
    seat: str
    count: int
    on_institute: int


class SovereignChanged(_Event):
    type: Literal["sovereign_changed"] = "sovereign_changed"
    seat: str  # new holder
    from_seat: str | None = None


class HouseAbilityTriggered(_Event):
    type: Literal["house_ability_triggered"] = "house_ability_triggered"
    seat: str
    house: House


class DecisionMade(_Event):
    """Records an answered decision, so replay can feed scripts the same choices."""

    type: Literal["decision_made"] = "decision_made"
    seat: str
    decision_id: int
    tokens: tuple[str, ...]


class TurnEnded(_Event):
    type: Literal["turn_ended"] = "turn_ended"
    seat: str


class GameEndTriggered(_Event):
    type: Literal["game_end_triggered"] = "game_end_triggered"
    by_seat: str
    turn_number: int


class GameEnded(_Event):
    type: Literal["game_ended"] = "game_ended"
    scores: dict[str, int]
    winners: tuple[str, ...]


Event = Annotated[
    GameStarted
    | CardDealt
    | CardsToLocation
    | TurnBegan
    | ActionChosen
    | Deployed
    | Placed
    | CardGained
    | CardDrawnToHand
    | Banished
    | CardMoved
    | CardStolen
    | Blocked
    | LocationBonus
    | DieRolled
    | HeliumChanged
    | FleetAdvanced
    | InfluencePlaced
    | SovereignChanged
    | HouseAbilityTriggered
    | DecisionMade
    | TurnEnded
    | GameEndTriggered
    | GameEnded,
    Field(discriminator="type"),
]

EventAdapter: TypeAdapter[Event] = TypeAdapter(Event)
