"""Static card definitions: the immutable printed face of all 112 cards.

Card *definitions* live here. Card *behaviour* (the deploy scripts) lives in
`red_rising.engine.cards`. Runtime card instances live in the game state.

The definitions are generated from `red_rising_characters.parquet` by
`red_rising/data/build_cards.py` into `red_rising/data/cards.json`, which is
checked in. The engine reads the JSON, never the parquet.
"""

from __future__ import annotations

from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator

from red_rising.enums import Color

CARDS_JSON = Path(__file__).parent / "data" / "cards.json"

TOTAL_CARDS = 112


class RefKind(StrEnum):
    COLOR = "color"
    CHARACTER = "character"
    KEYWORD = "keyword"


class Ref(BaseModel):
    """A resolved `[label](#anchor)` reference inside card text.

    `target` is canonical: a `Color` value, a card id, or a keyword. This is what
    lets a card script or the scoring parser answer "which card does this mean?"
    without re-parsing prose.
    """

    model_config = {"frozen": True}

    kind: RefKind
    label: str
    target: str


class Ability(BaseModel):
    model_config = {"frozen": True}

    text: str = Field(description="Human-readable, markdown links flattened to their labels")
    raw: str = Field(description="Original markdown, kept so the UI can render links")
    refs: tuple[Ref, ...] = ()

    def __str__(self) -> str:
        return self.text


class BonusClause(BaseModel):
    """One `N: condition` clause of an end-game bonus.

    `points is None` marks a variable award (printed as `?` on the card, e.g.
    "Gain points equal to your position on the Fleet Track"); the value is
    computed by a bespoke predicate at scoring time.
    """

    model_config = {"frozen": True}

    points: int | None
    condition: str
    raw: str
    refs: tuple[Ref, ...] = ()

    def __str__(self) -> str:
        pts = "?" if self.points is None else str(self.points)
        return f"{pts}: {self.condition}"


class CardDef(BaseModel):
    model_config = {"frozen": True}

    id: str
    name: str
    color: Color
    role: str
    core_value: int

    deploy: Ability | None = None
    block: Ability | None = None
    endgame: Ability | None = None
    bonuses: tuple[BonusClause, ...] = ()

    #: Optional portrait. Reserved now so art can be dropped in later without a
    #: schema migration; the UI falls back to a color field when absent.
    art_url: str | None = None

    @model_validator(mode="after")
    def _check_role_matches_caste(self) -> Self:
        if self.role != self.color.caste:
            raise ValueError(
                f"{self.id}: role {self.role!r} disagrees with {self.color} caste "
                f"{self.color.caste!r}"
            )
        return self

    @property
    def is_gold(self) -> bool:
        return self.color is Color.GOLD

    @property
    def is_wild_color(self) -> bool:
        """Gray cards may count as one additional color at scoring time."""
        return self.color is Color.GRAY

    @property
    def is_wild_name(self) -> bool:
        """Orange cards may take on any character's name at scoring time."""
        return self.color is Color.ORANGE


class CardIndex(BaseModel):
    """All card definitions, plus the lookups the engine actually asks for."""

    model_config = {"frozen": True}

    cards: tuple[CardDef, ...]

    @model_validator(mode="after")
    def _check_complete(self) -> Self:
        if len(self.cards) != TOTAL_CARDS:
            raise ValueError(f"expected {TOTAL_CARDS} cards, got {len(self.cards)}")
        ids = [c.id for c in self.cards]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate card ids")
        names = [c.name for c in self.cards]
        if len(set(names)) != len(names):
            raise ValueError("duplicate card names")
        return self

    @property
    def by_id(self) -> dict[str, CardDef]:
        return {c.id: c for c in self.cards}

    def __getitem__(self, card_id: str) -> CardDef:
        return self.by_id[card_id]

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self):  # type: ignore[override]
        return iter(self.cards)

    def of_color(self, color: Color) -> tuple[CardDef, ...]:
        return tuple(c for c in self.cards if c.color is color)


@cache
def load_cards(path: Path | None = None) -> CardIndex:
    """Load and validate the card index. Cached; the definitions are immutable."""
    src = path or CARDS_JSON
    return CardIndex.model_validate_json(src.read_text())
