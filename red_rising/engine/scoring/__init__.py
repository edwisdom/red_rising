"""End-game scoring.

`base` holds token scoring and orchestration; `scorers` holds the 102 per-card bonus
functions; `wildcards` optimises Gray/Orange assignments and is the entry point
`base.card_bonus_points` calls. Public API is re-exported here so callers keep
importing `red_rising.engine.scoring`.
"""

from __future__ import annotations

from . import scorers as _scorers  # noqa: F401  (populates the SCORERS registry)
from .base import (
    ScoreBreakdown,
    card_bonus_points,
    score_game,
    score_influence,
    winners,
)

__all__ = [
    "ScoreBreakdown",
    "card_bonus_points",
    "score_game",
    "score_influence",
    "winners",
]
