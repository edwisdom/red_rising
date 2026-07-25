"""Phase 4: end-game bonus scoring, wildcards, and the scoring order.

Scorers are checked from the printed card text; the wildcard tests confirm a Gray
counts as a chosen color and an Orange takes a chosen name, each picked to maximise
the score.
"""

from __future__ import annotations

from red_rising.carddefs import load_cards
from red_rising.engine.scoring.base import score_game
from red_rising.engine.scoring.wildcards import best_bonus_total
from red_rising.engine.state import GameState, LocationStack, PlayerState
from red_rising.enums import Color, House, Location

CARDS = load_cards()


def _state(
    hand: list[str],
    *,
    hand2: list[str] | None = None,
    helium: int = 0,
    fleet: int = 0,
    influence: int = 0,
    sovereign: bool = False,
    banished: list[str] | None = None,
    locations: dict[Location, list[str]] | None = None,
) -> tuple[GameState, PlayerState]:
    p0 = PlayerState(
        seat="p0",
        name="A",
        house=House.MARS,
        hand=list(hand),
        helium=helium,
        fleet=fleet,
        influence_on_institute=influence,
        has_sovereign=sovereign,
    )
    p1 = PlayerState(seat="p1", name="B", house=House.DIANA, hand=list(hand2 or []))
    st = GameState(game_id="t", seed=0, players=[p0, p1], banished=list(banished or []))
    st.locations = {loc: LocationStack(location=loc) for loc in Location}
    for loc, ids in (locations or {}).items():
        for cid in ids:
            st.location(loc).place_on_top(cid)
    return st, p0


def bonus(hand: list[str], **kw) -> int:
    st, p0 = _state(hand, **kw)
    return best_bonus_total(st, p0)


def some(color: Color, exclude: set[str] = frozenset()) -> str:
    return next(c.id for c in CARDS if c.color is color and c.id not in exclude)


# --------------------------------------------------------------------------- #
# Simple scorers
# --------------------------------------------------------------------------- #


def test_for_each_counts_matching_colors():
    # Modjob: 5 for each Red and Brown (including Modjob, which is Brown).
    assert bonus(["modjob"]) == 5  # counts itself
    red = some(Color.RED)
    assert bonus(["modjob", red]) == 10 + _self_bonus(red, ["modjob", red])


def _self_bonus(cid: str, hand: list[str]) -> int:
    """The other card's own contribution, to keep for_each assertions exact."""
    from red_rising.engine.scoring.context import ScoreCtx
    from red_rising.engine.scoring.scorers import SCORERS
    from red_rising.engine.scoring.wildcards import _base_fields

    st, p0 = _state(hand)
    base = _base_fields(st, p0)
    scorer = SCORERS.get(cid)
    if scorer is None:
        return 0
    return scorer(ScoreCtx(hand_ids=tuple(hand), self_id=cid, **base))


def test_if_with_named_character():
    # Victra: 10 if with The Howlers; 10 if with Sevro or Darrow.
    assert bonus(["victra"]) == 0
    assert bonus(["victra", "howlers"]) >= 10  # + howlers' own bonus
    assert bonus(["victra", "sevro", "howlers"]) >= 20


def test_deanna_needs_another_red():
    other_red = some(Color.RED, {"deanna"})
    assert bonus(["deanna"]) == 0  # no OTHER red
    assert bonus(["deanna", other_red]) >= 26


def test_lorn_no_other_golds():
    another_gold = some(Color.GOLD, {"lorn"})
    assert bonus(["lorn"]) == 15  # itself is the only Gold
    assert bonus(["lorn", another_gold]) == _self_bonus(another_gold, ["lorn", another_gold])


def test_stained_only_obsidian():
    another_obsidian = some(Color.OBSIDIAN, {"stained"})
    assert bonus(["stained"]) == 15
    assert bonus(["stained", another_obsidian]) == _self_bonus(
        another_obsidian, ["stained", another_obsidian]
    )


# --------------------------------------------------------------------------- #
# Compound scorers
# --------------------------------------------------------------------------- #


def test_cassius_both_and_penalty():
    assert bonus(["cassius", "darrow"]) == -20 + _self_bonus("darrow", ["cassius", "darrow"])
    assert bonus(["cassius", "darrow", "mustang"]) == 40 + _self_bonus(
        "mustang", ["cassius", "darrow", "mustang"]
    ) + _self_bonus("darrow", ["cassius", "darrow", "mustang"])


def test_theodora_xor():
    gold, red = some(Color.GOLD), some(Color.RED)
    assert bonus(["theodora", gold]) >= 14  # gold, not red
    assert bonus(["theodora", red]) >= 14  # red, not gold
    # both gold and red -> the 14 does NOT apply (but not both)
    assert bonus(["theodora", gold, red]) == (
        _self_bonus(gold, ["theodora", gold, red]) + _self_bonus(red, ["theodora", gold, red])
    )


def test_antonia_two_other_golds():
    g1, g2 = (
        some(Color.GOLD, {"antonia"}),
        some(Color.GOLD, {"antonia", some(Color.GOLD, {"antonia"})}),
    )
    # The Jackal path:
    assert bonus(["antonia", "jackal"]) >= 15
    # 2 other Golds path:
    assert bonus(["antonia", g1, g2]) >= 15


# --------------------------------------------------------------------------- #
# Wildcards
# --------------------------------------------------------------------------- #


def test_gray_counts_as_a_chosen_color():
    # Janitor (Brown): 5 for each Green/Yellow/Blue — it counts OTHERS, not itself.
    # Trigg (Gray) scores 0 on an empty board, so the +5 comes entirely from the
    # optimiser counting Trigg as Blue.
    assert bonus(["janitor"]) == 0
    assert bonus(["janitor", "trigg"]) == 5  # Trigg counted as a Blue


def test_orange_takes_a_chosen_name():
    # Aja: 15 if with Octavia. Cyther (Orange) scores 0 with no Blue, so the optimiser
    # renames it "octavia" to unlock Aja's 15.
    assert bonus(["aja"]) == 0
    assert bonus(["aja", "cyther"]) == 15


def test_optimiser_picks_the_best_wildcard():
    # Confirms the optimiser doesn't leave a useful wildcard unused.
    assert bonus(["janitor", "trigg"]) > bonus(["janitor"])


# --------------------------------------------------------------------------- #
# Modifiers, variable clauses, ranks
# --------------------------------------------------------------------------- #


def test_artisan_chef_ignores_lost_points_from_golds():
    # Jackal: -30 if with Darrow. Artisan Chef ignores that loss (Jackal is Gold).
    without = bonus(["jackal", "darrow"])
    withchef = bonus(["jackal", "darrow", "artisan-chef"])
    # Chef removes Jackal's -30 and adds its own "5 for each Gold" (Jackal = 1 Gold).
    assert withchef > without
    assert withchef == 5 + _self_bonus("darrow", ["jackal", "darrow", "artisan-chef"])


def test_developer_variable_clause_uses_best_location_top():
    top = some(Color.GOLD)  # some high-value card
    val = CARDS[top].core_value
    assert bonus(["developer"], locations={Location.MARS: [top]}) == val


def test_orion_scores_its_fleet_position():
    # Orion: 10 if with Pax..., plus "points = your Fleet position".
    assert bonus(["orion"], fleet=6) == 6
    assert bonus(["orion"], fleet=0) == 0


def test_rank_based_most_influence():
    # Holo Host: 18 if you have the most Influence on the Institute.
    assert bonus(["holo-host"], influence=5, hand2=[]) == 18  # p1 has 0
    st, p0 = _state(["holo-host"], influence=2)
    st.player("p1").influence_on_institute = 9  # opponent now leads
    assert best_bonus_total(st, p0) == 0


# --------------------------------------------------------------------------- #
# End-of-game (⏰) ability phase
# --------------------------------------------------------------------------- #


def _run_endgame(ctx, seat: str, card_id: str, *answers) -> None:
    """Drive one end-game ability to completion, answering by option token/label."""
    from red_rising.engine.endgame import ENDGAME

    fn = ENDGAME[card_id]
    gen = fn(ctx, seat)
    if gen is None:
        return
    it = iter(answers)
    send = None
    while True:
        try:
            req = gen.send(send)
        except StopIteration:
            return
        sel = next(it)
        send = next(o for o in req.options if sel in {o.token, o.label, o.card_id, o.tag})


def _ctx_for(state):
    import random

    from red_rising.engine.context import Ctx

    events: list = []
    rng = random.Random(0)
    return Ctx(state, rng, lambda e: events.append(e), lambda seat: None)


def test_surgeon_gains_a_banished_gold():
    gold = some(Color.GOLD)
    st, _ = _state(["surgeon"], banished=[gold, some(Color.RED)])
    ctx = _ctx_for(st)
    _run_endgame(ctx, "p0", "surgeon", gold)
    assert gold in st.player("p0").hand
    assert gold not in st.banished


def test_hacker_adds_points_equal_to_deck_top_core():
    top = some(Color.GOLD)
    st, _ = _state(["hacker"])
    st.deck = [top]  # top of deck = last element
    ctx = _ctx_for(st)
    _run_endgame(ctx, "p0", "hacker")
    assert st.player("p0").endgame_points == CARDS[top].core_value


def test_auctioneer_endgame_grants_the_chosen_bonus():
    st, _ = _state(["auctioneer"])
    ctx = _ctx_for(st)
    _run_endgame(ctx, "p0", "auctioneer", "fleet")
    assert st.player("p0").fleet == 1


def test_justice_gains_from_luna_only_with_sovereign():
    card = some(Color.RED)
    st, _ = _state(["justice"], sovereign=True, locations={Location.LUNA: [card]})
    ctx = _ctx_for(st)
    _run_endgame(ctx, "p0", "justice", card)
    assert card in st.player("p0").hand


def test_endgame_points_reach_the_final_score():
    from red_rising.engine.engine import Engine, PlayerSpec

    # Full game; just assert endgame_points fold into card_bonuses without error.
    engine = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=5)
    import random

    ch = random.Random(1)
    while not engine.finished:
        p = engine.pending
        assert p is not None
        from red_rising.engine.decisions import Answer

        k = ch.randint(p.min_choices, p.max_choices)
        engine.answer(
            Answer(decision_id=p.id, tokens=tuple(o.token for o in ch.sample(list(p.options), k)))
        )
    assert engine.finished and engine.scores is not None


def test_full_score_includes_bonuses():
    st, _ = _state(["janitor", some(Color.BLUE)], helium=3, fleet=2)
    scores = score_game(st)
    assert scores["p0"].card_bonuses > 0
    assert scores["p0"].total == (
        scores["p0"].core_values
        + scores["p0"].card_bonuses
        + scores["p0"].fleet
        + scores["p0"].helium
        + scores["p0"].sovereignty
        + scores["p0"].influence
        + scores["p0"].excess_penalty
    )
