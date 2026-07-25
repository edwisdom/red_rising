"""End-game scoring — base (tokens + core values) and orchestration.

The token parts (fleet track, helium, sovereignty, influence ranking, excess-card
penalty) live here. Card end-game *bonuses* — the 127 `N: condition` clauses and the
Gray/Orange wildcard optimisation — are computed by the sibling modules and plugged
in through `card_bonus_points`.

The scoring ORDER follows the rulebook exactly.
"""

from __future__ import annotations

from pydantic import BaseModel

from red_rising.carddefs import load_cards
from red_rising.enums import (
    EXCESS_CARD_PENALTY,
    FLEET_TRACK_POINTS,
    HAND_SIZE_LIMIT,
    HELIUM_POINTS,
    SOVEREIGN_POINTS,
)

from ..state import GameState, PlayerState

NEUTRAL = "__neutral__"


class ScoreBreakdown(BaseModel):
    """Per-seat score, itemised so the UI and tests can see where points came from."""

    seat: str
    core_values: int = 0
    card_bonuses: int = 0
    fleet: int = 0
    helium: int = 0
    sovereignty: int = 0
    influence: int = 0
    excess_penalty: int = 0  # <= 0

    @property
    def total(self) -> int:
        return (
            self.core_values
            + self.card_bonuses
            + self.fleet
            + self.helium
            + self.sovereignty
            + self.influence
            + self.excess_penalty
        )


def card_bonus_points(state: GameState, player: PlayerState) -> int:
    """End-game card bonuses for `player`, wildcards optimised. See `wildcards`."""
    from .wildcards import best_bonus_total

    return best_bonus_total(state, player)


def _influence_rate(count: int, tiers: list[int]) -> int:
    """4 points/token for the most, 2 for the second most, else 1."""
    if not tiers or count == 0:
        return 1
    if count == tiers[0]:
        return 4
    if len(tiers) > 1 and count == tiers[1]:
        return 2
    return 1


def score_influence(state: GameState) -> dict[str, int]:
    """Rank all houses (players + a 2-player neutral) by Institute influence."""
    counts: dict[str, int] = {p.seat: p.influence_on_institute for p in state.players}
    entrant_counts = list(counts.values())
    if state.neutral_influence > 0:
        entrant_counts.append(state.neutral_influence)  # neutral affects tiers, scores nothing
    tiers = sorted({c for c in entrant_counts if c > 0}, reverse=True)
    return {seat: count * _influence_rate(count, tiers) for seat, count in counts.items()}


def score_game(state: GameState) -> dict[str, ScoreBreakdown]:
    cards = load_cards()
    influence_points = score_influence(state)
    result: dict[str, ScoreBreakdown] = {}

    for player in state.players:
        core = sum(cards[cid].core_value for cid in player.hand)
        excess = max(0, len(player.hand) - HAND_SIZE_LIMIT) * EXCESS_CARD_PENALTY
        result[player.seat] = ScoreBreakdown(
            seat=player.seat,
            core_values=core,
            card_bonuses=card_bonus_points(state, player) + player.endgame_points,
            fleet=FLEET_TRACK_POINTS[player.fleet],
            helium=player.helium * HELIUM_POINTS,
            sovereignty=SOVEREIGN_POINTS if player.has_sovereign else 0,
            influence=influence_points[player.seat],
            excess_penalty=-excess,
        )
    return result


def winners(scores: dict[str, ScoreBreakdown], state: GameState) -> tuple[str, ...]:
    """Highest score wins; ties broken by the Sovereign token, else shared."""
    best = max(s.total for s in scores.values())
    tied = [seat for seat, s in scores.items() if s.total == best]
    if len(tied) > 1 and state.sovereign_holder in tied:
        return (state.sovereign_holder,)
    return tuple(tied)
