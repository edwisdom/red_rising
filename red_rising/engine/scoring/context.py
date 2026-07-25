"""`ScoreCtx`: the read-only view a per-card scorer evaluates against.

A `ScoreCtx` captures one player's final position *under one wildcard assignment*
(each Gray card counts as one extra color; each Orange card takes a character's
name). The wildcard optimiser builds many contexts and keeps the best-scoring one.

Scorers ask questions through the wildcard-aware helpers here — `has`, `count`,
`for_each` — so a Gray-as-Blue is found by a "Blue" query and an Orange-as-Darrow by
a "Darrow" query, exactly as the rules intend.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from red_rising.carddefs import CardIndex
from red_rising.enums import Color, Location

# A scorer target is either a caste Color or a card id (a character name).
Target = Color | str


@dataclass(frozen=True)
class ScoreCtx:
    cards: CardIndex
    hand_ids: tuple[str, ...]
    self_id: str  # the card whose clauses are being scored ("this"/"other")

    # Wildcard assignment for this evaluation.
    gray_color: dict[str, Color] = field(default_factory=dict)
    orange_name: dict[str, str] = field(default_factory=dict)

    # Player tokens.
    helium: int = 0
    fleet: int = 0
    influence: int = 0
    has_sovereign: bool = False

    # Cross-player ranks (wildcard-independent; precomputed by the orchestrator).
    most_influence: bool = False
    least_influence: bool = False
    most_helium: bool = False
    most_fleet: bool = False
    opp_more_fleet: bool = False
    opp_more_helium: bool = False
    ties_influence_with_opp: bool = False
    fewest_cards: bool = False

    # Board / banished.
    banished: frozenset[str] = frozenset()
    banished_count: int = 0
    board_ids: tuple[str, ...] = ()  # every face-up card on any location
    location_top: dict[Location, str | None] = field(default_factory=dict)
    a_location_empty_or_facedown: bool = False

    # ---- wildcard-aware card queries ----

    @property
    def n_cards(self) -> int:
        return len(self.hand_ids)

    def _colors(self, cid: str) -> set[Color]:
        colors = {self.cards[cid].color}
        extra = self.gray_color.get(cid)
        if extra is not None:
            colors.add(extra)
        return colors

    def _name(self, cid: str) -> str:
        return self.orange_name.get(cid, cid)

    def _matches(self, cid: str, colors: set[Color], names: set[str]) -> bool:
        return bool(self._colors(cid) & colors) or self._name(cid) in names

    def count(self, *targets: Target, exclude_self: bool = False) -> int:
        # Color is a StrEnum, so exclude it explicitly from the name set.
        colors = {t for t in targets if isinstance(t, Color)}
        names = {t for t in targets if isinstance(t, str) and not isinstance(t, Color)}
        return sum(
            1
            for cid in self.hand_ids
            if not (exclude_self and cid == self.self_id) and self._matches(cid, colors, names)
        )

    def has(self, *targets: Target) -> bool:
        return self.count(*targets) > 0

    def has_other(self, *targets: Target) -> bool:
        """Has a matching card OTHER than the one being scored."""
        return self.count(*targets, exclude_self=True) > 0

    def for_each(self, *targets: Target, exclude_self: bool = False) -> int:
        return self.count(*targets, exclude_self=exclude_self)

    def all_cards_are(self, *colors: Color) -> bool:
        """Every card in hand has one of `colors` as its printed color."""
        allowed = set(colors)
        return all(self.cards[cid].color in allowed for cid in self.hand_ids)

    def all_cards(self, predicate) -> bool:
        return all(predicate(self.cards[cid]) for cid in self.hand_ids)

    def core_values(self) -> list[int]:
        return [self.cards[cid].core_value for cid in self.hand_ids]

    def distinct_colors(self) -> bool:
        colors = [self.cards[cid].color for cid in self.hand_ids]
        return len(set(colors)) == len(colors)

    def distinct_initials(self) -> bool:
        initials = [self.cards[cid].name[0].upper() for cid in self.hand_ids]
        return len(set(initials)) == len(initials)

    def banished_has_color(self, color: Color) -> bool:
        return any(self.cards[cid].color is color for cid in self.banished)

    def count_banished(self, *colors: Color) -> int:
        allowed = set(colors)
        return sum(1 for cid in self.banished if self.cards[cid].color in allowed)

    def count_on_board(self, *colors: Color) -> int:
        """Face-up cards of `colors` across all locations (wildcards don't apply here)."""
        allowed = set(colors)
        return sum(1 for cid in self.board_ids if self.cards[cid].color in allowed)

    def max_location_top_core(self) -> int:
        tops = [t for t in self.location_top.values() if t is not None]
        return max((self.cards[t].core_value for t in tops), default=0)

    # ---- convenience ----

    @staticmethod
    def pts(condition: bool, value: int) -> int:
        return value if condition else 0
