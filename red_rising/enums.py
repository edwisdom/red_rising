"""Shared vocabulary for the Red Rising domain.

Deliberately dependency-free: every other module may import this, and it may
import nothing from the project.
"""

from enum import StrEnum


class Color(StrEnum):
    """The 14 castes. Values match the `color` column of the source parquet."""

    RED = "Red"
    PINK = "Pink"
    ORANGE = "Orange"
    YELLOW = "Yellow"
    GREEN = "Green"
    COPPER = "Copper"
    SILVER = "Silver"
    GOLD = "Gold"
    BLUE = "Blue"
    VIOLET = "Violet"
    WHITE = "White"
    GRAY = "Gray"
    BROWN = "Brown"
    OBSIDIAN = "Obsidian"

    @property
    def caste(self) -> str:
        return _CASTE[self]

    @property
    def hex(self) -> str:
        return _HEX[self]


_CASTE: dict[Color, str] = {
    Color.RED: "laborer",
    Color.PINK: "companion",
    Color.ORANGE: "engineer",
    Color.YELLOW: "doctor",
    Color.GREEN: "programmer",
    Color.COPPER: "bureaucrat",
    Color.SILVER: "financier",
    Color.GOLD: "elite",
    Color.BLUE: "pilot",
    Color.VIOLET: "artist",
    Color.WHITE: "arbitrator",
    Color.GRAY: "security",
    Color.BROWN: "assistant",
    Color.OBSIDIAN: "assassin",
}

# Display colors for the frontend. Tuned for legibility on a dark table felt
# rather than for literal accuracy (a literal Yellow/White is unreadable).
_HEX: dict[Color, str] = {
    Color.RED: "#c0392b",
    Color.PINK: "#e78ba8",
    Color.ORANGE: "#d97b2b",
    Color.YELLOW: "#d4b13a",
    Color.GREEN: "#3f9e5a",
    Color.COPPER: "#a5673f",
    Color.SILVER: "#9aa4ad",
    Color.GOLD: "#c8a227",
    Color.BLUE: "#3a6ea5",
    Color.VIOLET: "#8e5ba6",
    Color.WHITE: "#dfe3e6",
    Color.GRAY: "#6b7178",
    Color.BROWN: "#7a5230",
    Color.OBSIDIAN: "#2b2f33",
}

#: Plural forms as used in card text ("banish all Golds"), for anchor resolution.
COLOR_BY_PLURAL: dict[str, Color] = {f"{c.value.lower()}s": c for c in Color}


class Location(StrEnum):
    """The 4 locations. The deck is NOT a location (rulebook, "Important Notes")."""

    JUPITER = "Jupiter"
    MARS = "Mars"
    LUNA = "Luna"
    INSTITUTE = "Institute"

    @property
    def display(self) -> str:
        return "The Institute" if self is Location.INSTITUTE else self.value


class House(StrEnum):
    APOLLO = "Apollo"
    CERES = "Ceres"
    DIANA = "Diana"
    JUPITER = "Jupiter"
    MARS = "Mars"
    MINERVA = "Minerva"

    @property
    def hex(self) -> str:
        return _HOUSE_HEX[self]


_HOUSE_HEX: dict[House, str] = {
    House.APOLLO: "#d4b13a",  # yellow
    House.CERES: "#7a5230",  # brown
    House.DIANA: "#3f9e5a",  # green
    House.JUPITER: "#3a6ea5",  # blue
    House.MARS: "#c0392b",  # red
    House.MINERVA: "#8e5ba6",  # purple
}


class DieFace(StrEnum):
    """The 6 faces of the Rising die."""

    BANISH = "banish"
    REVEAL = "reveal"
    SOVEREIGN = "sovereign"
    HELIUM = "helium"
    FLEET = "fleet"
    INFLUENCE = "influence"


#: Fleet Track scoring, indexed by track position 0..10.
FLEET_TRACK_POINTS: tuple[int, ...] = (0, 1, 3, 6, 10, 15, 21, 28, 34, 39, 43)

MAX_FLEET = 10
MAX_INFLUENCE = 10
HAND_SIZE_LIMIT = 7  # cards beyond this cost 10 points each
STARTING_HAND = 5
CARDS_PER_LOCATION_AT_SETUP = 2
HELIUM_POINTS = 3
SOVEREIGN_POINTS = 10
EXCESS_CARD_PENALTY = 10

#: Game end triggers when all 3 thresholds are met across players, or any 2 by
#: one player.
END_THRESHOLD = 7
