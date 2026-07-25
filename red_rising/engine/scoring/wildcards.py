"""Gray/Orange wildcard optimisation and the bonus-scoring orchestrator.

Each Gray card may count as one additional color, and each Orange card may take any
character's name. Those choices are the player's, made to maximise their score, so we
search assignments and keep the best total.

The search is bounded: Orange candidates are only the character names some clause in
the hand actually checks (a handful); Gray candidates are the 14 colors. When the
product would be large (many wildcards), we fall back to a greedy hill-climb. For a
normal ≤7-card hand the exact search is tiny.
"""

from __future__ import annotations

import itertools

from red_rising.carddefs import RefKind, load_cards
from red_rising.enums import Color

from ..state import GameState, PlayerState
from .context import ScoreCtx
from .scorers import SCORERS

#: Cap on the exact-search product size before falling back to greedy.
_EXACT_CAP = 200_000


def _base_fields(state: GameState, player: PlayerState) -> dict:
    """Everything a ScoreCtx needs that does NOT depend on the wildcard assignment."""
    cards = load_cards()
    others = [p for p in state.players if p.seat != player.seat]

    influences = [p.influence_on_institute for p in state.players]
    heliums = [p.helium for p in state.players]
    fleets = [p.fleet for p in state.players]
    hand_sizes = [len(p.hand) for p in state.players]

    board_ids: list[str] = []
    location_top: dict = {}
    empty_or_facedown = False
    for loc, stack in state.locations.items():
        top = stack.top()
        location_top[loc] = top.card_id if (top and not top.face_down) else None
        if stack.is_empty or (top is not None and top.face_down):
            empty_or_facedown = True
        board_ids.extend(c.card_id for c in stack.cards if not c.face_down)

    return {
        "cards": cards,
        "helium": player.helium,
        "fleet": player.fleet,
        "influence": player.influence_on_institute,
        "has_sovereign": player.has_sovereign,
        "most_influence": player.influence_on_institute == max(influences),
        "least_influence": player.influence_on_institute == min(influences),
        "most_helium": player.helium == max(heliums),
        "most_fleet": player.fleet == max(fleets),
        "opp_more_fleet": any(o.fleet > player.fleet for o in others),
        "opp_more_helium": any(o.helium > player.helium for o in others),
        "ties_influence_with_opp": any(
            o.influence_on_institute == player.influence_on_institute for o in others
        ),
        "fewest_cards": len(player.hand) == min(hand_sizes),
        "banished": frozenset(state.banished),
        "banished_count": len(state.banished),
        "board_ids": tuple(board_ids),
        "location_top": location_top,
        "a_location_empty_or_facedown": empty_or_facedown,
    }


def _referenced_names(hand: tuple[str, ...]) -> list[str]:
    """Character ids that any clause in the hand cares about (Orange candidates)."""
    cards = load_cards()
    names: set[str] = set()
    for cid in hand:
        card = cards[cid]
        for source in (card.deploy, card.block, card.endgame, *card.bonuses):
            if source is None:
                continue
            for ref in source.refs:
                if ref.kind is RefKind.CHARACTER:
                    names.add(ref.target)
    return sorted(names)


def _bonus_total(
    hand: tuple[str, ...],
    gray_color: dict[str, Color],
    orange_name: dict[str, str],
    base: dict,
    *,
    artisan_chef: bool,
) -> int:
    total = 0
    for cid in hand:
        scorer = SCORERS.get(cid)
        if scorer is None:
            continue
        ctx = ScoreCtx(
            hand_ids=hand, self_id=cid, gray_color=gray_color, orange_name=orange_name, **base
        )
        pts = scorer(ctx)
        # House Ceres / Artisan Chef end-game: ignore points lost from Gold cards.
        if artisan_chef and base["cards"][cid].is_gold and pts < 0:
            pts = 0
        total += pts
    return total


def best_bonus_total(state: GameState, player: PlayerState) -> int:
    cards = load_cards()
    hand = tuple(player.hand)
    if not hand:
        return 0
    base = _base_fields(state, player)
    artisan_chef = "artisan-chef" in hand

    grays = [c for c in hand if cards[c].color is Color.GRAY]
    oranges = [c for c in hand if cards[c].color is Color.ORANGE]

    gray_options: list[Color | None] = [None, *list(Color)]
    orange_options: list[str | None] = [None, *_referenced_names(hand)]

    def evaluate(gmap: dict[str, Color], omap: dict[str, str]) -> int:
        return _bonus_total(hand, gmap, omap, base, artisan_chef=artisan_chef)

    product_size = len(gray_options) ** len(grays) * len(orange_options) ** len(oranges)
    if product_size <= _EXACT_CAP:
        best = evaluate({}, {})
        for gcombo in itertools.product(gray_options, repeat=len(grays)):
            gmap = {g: c for g, c in zip(grays, gcombo, strict=True) if c is not None}
            for ocombo in itertools.product(orange_options, repeat=len(oranges)):
                omap = {o: n for o, n in zip(oranges, ocombo, strict=True) if n is not None}
                best = max(best, evaluate(gmap, omap))
        return best

    return _greedy(grays, oranges, gray_options, orange_options, evaluate)


def _greedy(grays, oranges, gray_options, orange_options, evaluate) -> int:
    """Hill-climb: repeatedly set each wildcard to its best value until stable."""
    gmap: dict[str, Color] = {}
    omap: dict[str, str] = {}
    improved = True
    best = evaluate(gmap, omap)
    while improved:
        improved = False
        for g in grays:
            for opt in gray_options:
                trial = dict(gmap)
                if opt is None:
                    trial.pop(g, None)
                else:
                    trial[g] = opt
                val = evaluate(trial, omap)
                if val > best:
                    best, gmap, improved = val, trial, True
        for o in oranges:
            for opt in orange_options:
                trial = dict(omap)
                if opt is None:
                    trial.pop(o, None)
                else:
                    trial[o] = opt
                val = evaluate(gmap, trial)
                if val > best:
                    best, omap, improved = val, trial, True
    return best
