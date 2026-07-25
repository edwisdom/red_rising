"""Phase 1: the engine skeleton.

Covers the load-bearing invariants (card conservation, termination, replay
determinism), turn scheduling (equal turns, Apollo's bonus turn), and the base
scoring math. Card abilities are Phase 3; scoring bonuses are Phase 4.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from red_rising.engine.decisions import Answer
from red_rising.engine.engine import Engine, IllegalAnswer, PlayerSpec
from red_rising.engine.random_driver import play_random_game
from red_rising.engine.scoring import ScoreBreakdown, score_influence
from red_rising.engine.state import GameState, PlayerState
from red_rising.enums import (
    FLEET_TRACK_POINTS,
    MAX_FLEET,
    MAX_INFLUENCE,
    House,
    Location,
)


def _random_answer(engine: Engine, chooser: random.Random) -> Answer:
    p = engine.pending
    assert p is not None
    k = chooser.randint(p.min_choices, p.max_choices)
    tokens = tuple(o.token for o in chooser.sample(list(p.options), k))
    return Answer(decision_id=p.id, tokens=tokens)


def _drive(engine: Engine, chooser: random.Random, on_action=None) -> None:
    """Play to completion, invoking `on_action(seat)` at each top-level action choice."""
    while not engine.finished:
        p = engine.pending
        assert p is not None
        if on_action is not None and p.kind == "action":
            on_action(p.seat)
        engine.answer(_random_answer(engine, chooser))


def _answers_of(engine: Engine, chooser: random.Random) -> list[Answer]:
    """Play a game randomly, returning the exact answer sequence used."""
    answers: list[Answer] = []
    while not engine.finished:
        a = _random_answer(engine, chooser)
        answers.append(a)
        engine.answer(a)
    return answers


# --------------------------------------------------------------------------- #
# Invariants
# --------------------------------------------------------------------------- #


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 10_000), n=st.integers(2, 6))
def test_every_game_terminates_and_conserves_cards(seed: int, n: int):
    engine = play_random_game(seed, n)
    assert engine.finished
    engine.state.assert_card_conservation()  # also asserted after every turn internally


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 10_000), n=st.integers(2, 6))
def test_resource_bounds_hold_at_end(seed: int, n: int):
    engine = play_random_game(seed, n)
    for p in engine.state.players:
        assert p.helium >= 0
        assert 0 <= p.fleet <= MAX_FLEET
        assert 0 <= p.influence_on_institute <= MAX_INFLUENCE
        assert p.influence_supply + p.influence_on_institute == MAX_INFLUENCE
    holders = [p for p in engine.state.players if p.has_sovereign]
    assert len(holders) <= 1


def test_replay_from_recorded_answers_is_deterministic():
    """Same seed + same answers => byte-identical event log. The regression bedrock."""
    chooser = random.Random(999)
    engine_a = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=7)
    answers = _answers_of(engine_a, chooser)

    engine_b = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=7)
    for a in answers:
        # decision ids are assigned deterministically, so they line up on replay
        engine_b.answer(a)

    assert engine_b.finished
    dump_a = [e.model_dump() for e in engine_a.events]
    dump_b = [e.model_dump() for e in engine_b.events]
    assert dump_a == dump_b


def test_two_games_same_seed_identical():
    a = play_random_game(1234, 2)
    b = play_random_game(1234, 2)
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


# --------------------------------------------------------------------------- #
# Setup & scheduling
# --------------------------------------------------------------------------- #


def test_setup_deals_the_expected_opening():
    engine = Engine.new_game(
        [PlayerSpec(name="A", house=House.MARS), PlayerSpec(name="B", house=House.DIANA)],
        seed=3,
    )
    st_ = engine.state
    for loc in Location:
        assert len(st_.location(loc).cards) == 2  # 2 face up per location
    # 5-card opening hands (neither is Ceres), 2-player neutral influence seeded.
    assert all(len(p.hand) == 5 for p in st_.players)
    assert st_.neutral_influence == 3
    # 112 - 8 on board - 10 in hands = 94 in deck.
    assert len(st_.deck) == 112 - 8 - 10


def test_ceres_starts_with_an_extra_card():
    engine = Engine.new_game(
        [PlayerSpec(name="A", house=House.CERES), PlayerSpec(name="B", house=House.MARS)],
        seed=3,
    )
    hands = {p.house: len(p.hand) for p in engine.state.players}
    assert hands[House.CERES] == 6
    assert hands[House.MARS] == 5


def test_apollo_leads_and_takes_the_final_bonus_turn():
    chooser = random.Random(5)
    engine = Engine.new_game(
        [PlayerSpec(name="A", house=House.MARS), PlayerSpec(name="B", house=House.APOLLO)],
        seed=11,
    )
    assert engine.state.players[0].house is House.APOLLO  # rotated to lead

    turn_seats: list[str] = []
    apollo = next(p.seat for p in engine.state.players if p.house is House.APOLLO)
    _drive(engine, chooser, on_action=turn_seats.append)

    assert turn_seats[0] == apollo, "Apollo takes the first turn"
    assert turn_seats[-1] == apollo, "Apollo takes the last (bonus) turn"
    assert engine.state.apollo_bonus_taken


def test_players_take_equal_turns_without_apollo():
    chooser = random.Random(8)
    engine = Engine.new_game(
        [PlayerSpec(name="A", house=House.MARS), PlayerSpec(name="B", house=House.DIANA)],
        seed=22,
    )
    counts = {p.seat: 0 for p in engine.state.players}
    _drive(engine, chooser, on_action=lambda seat: counts.__setitem__(seat, counts[seat] + 1))
    assert len(set(counts.values())) == 1, f"unequal turns: {counts}"


# --------------------------------------------------------------------------- #
# Illegal answers
# --------------------------------------------------------------------------- #


def test_stale_and_unknown_answers_are_rejected():
    engine = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=1)
    p = engine.pending
    assert p is not None
    with pytest.raises(IllegalAnswer):
        engine.answer(Answer(decision_id=p.id + 99, tokens=(p.options[0].token,)))
    with pytest.raises(IllegalAnswer):
        engine.answer(Answer(decision_id=p.id, tokens=("tag:nonsense",)))


# --------------------------------------------------------------------------- #
# Scoring math (base only)
# --------------------------------------------------------------------------- #


def _two_player_state(**overrides) -> GameState:
    players = [
        PlayerState(seat="p0", name="A", house=House.MARS),
        PlayerState(seat="p1", name="B", house=House.DIANA),
    ]
    for p in players:
        p.influence_supply = MAX_INFLUENCE
    st_ = GameState(game_id="t", seed=0, players=players)
    for k, v in overrides.items():
        setattr(st_, k, v)
    return st_


def test_influence_ranking_matches_rulebook_example():
    """Jamey 10, Megan 10, Biddy 5, Walter 2 -> 40, 40, 10, 2."""
    players = [
        PlayerState(seat="jamey", name="Jamey", house=House.MARS, influence_on_institute=10),
        PlayerState(seat="megan", name="Megan", house=House.DIANA, influence_on_institute=10),
        PlayerState(seat="biddy", name="Biddy", house=House.JUPITER, influence_on_institute=5),
        PlayerState(seat="walter", name="Walter", house=House.CERES, influence_on_institute=2),
    ]
    st_ = GameState(game_id="t", seed=0, players=players)
    pts = score_influence(st_)
    assert pts == {"jamey": 40, "megan": 40, "biddy": 10, "walter": 2}


def test_neutral_influence_participates_in_ranking_but_scores_nothing():
    st_ = _two_player_state(neutral_influence=8)
    st_.player("p0").influence_on_institute = 5
    st_.player("p1").influence_on_institute = 3
    pts = score_influence(st_)
    # Neutral(8) is the most, so both players are pushed down a tier:
    # p0's 5 is the "second most" -> 2/token; p1's 3 -> 1/token.
    assert pts == {"p0": 10, "p1": 3}


def test_fleet_helium_sovereign_and_excess_penalty():
    b = ScoreBreakdown(
        seat="p0",
        core_values=50,
        fleet=FLEET_TRACK_POINTS[7],  # 28
        helium=4 * 3,
        sovereignty=10,
        influence=0,
        excess_penalty=-20,  # two cards past the 7th
    )
    assert b.total == 50 + 28 + 12 + 10 + 0 - 20


def test_full_score_breakdown_adds_up():
    engine = play_random_game(42, 2)
    assert engine.scores is not None
    for seat, s in engine.scores.items():
        assert s.seat == seat
        # total is internally consistent with its parts
        assert s.total == (
            s.core_values
            + s.card_bonuses
            + s.fleet
            + s.helium
            + s.sovereignty
            + s.influence
            + s.excess_penalty
        )
