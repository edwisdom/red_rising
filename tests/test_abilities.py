"""Phase 3a: deploy-ability scripts (T0 + T1, 59 cards).

Two layers:
* a parametrised smoke test that runs *every* registered ability on a generic board
  and asserts it neither crashes nor loses/duplicates a card;
* targeted tests written from the printed card text for the interesting behaviours.

The harness drives a single ability in isolation: it seats a controlled board, puts
the source card on top of a location (as a deploy would), then pumps `trigger_deploy`,
answering each decision from a small selector list.
"""

from __future__ import annotations

import random

import pytest

from red_rising.carddefs import load_cards
from red_rising.engine import cards as _cards  # noqa: F401  (populates REGISTRY)
from red_rising.engine.abilities import REGISTRY, trigger_deploy
from red_rising.engine.context import Ctx
from red_rising.engine.decisions import DecisionRequest, Option
from red_rising.engine.events import DieRolled
from red_rising.engine.state import GameState, LocationStack, PlayerState
from red_rising.enums import Color, DieFace, House, Location

CARDS = load_cards()


def some(color: Color, exclude: set[str] = frozenset()) -> str:
    """Any card id of `color` not in `exclude`."""
    return next(c.id for c in CARDS if c.color is color and c.id not in exclude)


class Harness:
    def __init__(self, houses=(House.MARS, House.DIANA)) -> None:
        self.players = [
            PlayerState(seat=f"p{i}", name=f"P{i}", house=h) for i, h in enumerate(houses)
        ]
        self.state = GameState(game_id="t", seed=0, players=self.players)
        self.state.locations = {loc: LocationStack(location=loc) for loc in Location}
        self.events: list = []
        self.rng = random.Random(0)
        self.ctx = Ctx(self.state, self.rng, self._emit, self._roll)

    def _emit(self, e) -> None:
        self.events.append(e.model_copy(update={"seq": len(self.events)}))

    def _roll(self, seat: str) -> DieFace:
        face = self.rng.choice(list(DieFace))
        self._emit(DieRolled(seat=seat, face=face))
        return face

    # -- board setup --

    def place(self, loc: Location, *card_ids: str, face_down: bool = False) -> None:
        for cid in card_ids:  # bottom -> top
            self.state.location(loc).place_on_top(cid, face_down=face_down)

    def deck(self, *card_ids: str) -> None:
        self.state.deck = list(card_ids)  # last = top

    def hand(self, seat: str, *card_ids: str) -> None:
        self.state.player(seat).hand = list(card_ids)

    def banished(self, *card_ids: str) -> None:
        self.state.banished = list(card_ids)

    # -- run one ability --

    def run(self, card_id: str, loc: Location, *answers, seat: str = "p0") -> bool:
        # Mirror a real deploy: the source sits on top of its location. Tests that
        # pre-place the source (to control what's beneath it) skip this.
        if self.state.location(loc).index_of(card_id) is None:
            self.state.location(loc).place_on_top(card_id)
        gen = trigger_deploy(self.ctx, seat, card_id, loc)
        it = iter(answers)
        send = None
        while True:
            try:
                req: DecisionRequest = gen.send(send)
            except StopIteration as stop:
                return bool(stop.value)
            send = _pick(req, next(it))


def _pick(req: DecisionRequest, selector) -> Option:
    if callable(selector):
        return selector(req)
    for o in req.options:
        candidates = {o.token, o.label, o.card_id, o.tag, o.seat}
        if o.location is not None:
            candidates.add(o.location.value)
        if selector in candidates:
            return o
    raise KeyError(f"{selector!r} not among {[o.token for o in req.options]}")


# --------------------------------------------------------------------------- #
# Smoke: every ability runs and conserves cards
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("card_id", sorted(REGISTRY))
def test_every_ability_runs_and_conserves_cards(card_id: str):
    """Generic board, first option for every decision — no crash, no lost/dup card."""
    h = Harness()
    src = CARDS[card_id]
    # Two filler cards beneath the source, distinct from it and each other.
    used = {card_id}
    under = some(Color.GOLD if not src.is_gold else Color.RED, used)
    used.add(under)
    other = some(Color.BLUE, used)
    used.add(other)
    h.place(Location.MARS, other, under, card_id)  # source on top
    h.place(Location.JUPITER, some(Color.RED, used))
    used.add(h.state.location(Location.JUPITER).top().card_id)
    h.deck(some(Color.PINK, used), some(Color.GREEN, used | {some(Color.PINK, used)}))
    h.banished(some(Color.WHITE, used))
    h.state.player("p0").has_sovereign = True  # exercise sovereign-gated branches

    before = sorted(h.state.all_card_ids())
    # Answer every decision with its first option, up to a sane cap.
    h.run(card_id, Location.MARS, *[(lambda r: r.options[0])] * 12)
    after = sorted(h.state.all_card_ids())
    assert before == after, f"{card_id} lost/duplicated a card"


# --------------------------------------------------------------------------- #
# Targeted correctness
# --------------------------------------------------------------------------- #


def test_deanna_gains_helium():
    h = Harness()
    h.run("deanna", Location.MARS)
    assert h.state.player("p0").helium == 1


def test_uncle_narol_gains_two_helium():
    h = Harness()
    h.run("uncle-narol", Location.MARS)
    assert h.state.player("p0").helium == 2


def test_fleet_wave_advances_self_two_others_one():
    h = Harness()
    h.run("pelus", Location.JUPITER)
    assert h.state.player("p0").fleet == 2
    assert h.state.player("p1").fleet == 1


def test_invictus_only_on_mars():
    on = Harness()
    on.run("invictus", Location.MARS)
    assert on.state.player("p0").fleet == 1
    off = Harness()
    off.run("invictus", Location.JUPITER)
    assert off.state.player("p0").fleet == 0


def test_boneriders_gains_sovereign_and_triggers_house():
    h = Harness(houses=(House.MARS, House.DIANA))  # Mars house => gain 1 helium
    h.run("boneriders", Location.LUNA)
    assert h.state.sovereign_holder == "p0"
    assert h.state.player("p0").helium == 1  # house tile fired


def test_lorn_banishes_gold_directly_under():
    h = Harness()
    gold = some(Color.GOLD, {"lorn"})
    h.place(Location.MARS, gold, "lorn")  # lorn on top of a Gold
    h.run("lorn", Location.MARS)
    assert gold in h.state.banished
    assert h.state.location(Location.MARS).card_ids() == ["lorn"]


def test_lorn_ignores_non_gold_under():
    h = Harness()
    red = some(Color.RED)
    h.place(Location.MARS, red, "lorn")
    h.run("lorn", Location.MARS)
    assert not h.state.banished


def test_cassius_gains_gold_under_and_survives():
    h = Harness()
    gold = some(Color.GOLD, {"cassius"})
    h.place(Location.MARS, gold, "cassius")
    h.run("cassius", Location.MARS)
    assert gold in h.state.player("p0").hand
    assert "cassius" not in h.state.banished  # survives because under was a Gold


def test_cassius_self_banishes_when_under_not_gold():
    h = Harness()
    red = some(Color.RED)
    h.place(Location.MARS, red, "cassius")
    h.run("cassius", Location.MARS)
    assert red in h.state.player("p0").hand
    assert "cassius" in h.state.banished


def test_assassin_gold_under_places_influence():
    h = Harness()
    gold = some(Color.GOLD)
    h.place(Location.MARS, gold, "assassin")
    h.run("assassin", Location.MARS)
    assert gold in h.state.banished
    assert h.state.player("p0").influence_on_institute == 1


def test_ash_lord_regains_when_two_blues_banished():
    h = Harness()
    b1, b2 = some(Color.BLUE), some(Color.BLUE, {some(Color.BLUE)})
    h.place(Location.MARS, b1, b2, "ash-lord")
    h.run("ash-lord", Location.MARS)
    assert b1 in h.state.banished and b2 in h.state.banished
    assert "ash-lord" in h.state.player("p0").hand  # regained


def test_ash_lord_stays_with_one_blue():
    h = Harness()
    blue = some(Color.BLUE)
    h.place(Location.MARS, blue, "ash-lord")
    h.run("ash-lord", Location.MARS)
    assert blue in h.state.banished
    assert "ash-lord" not in h.state.player("p0").hand


def test_evey_banishes_all_here_and_scores_golds():
    h = Harness()
    g1, g2 = some(Color.GOLD), some(Color.GOLD, {some(Color.GOLD)})
    red = some(Color.RED)
    h.place(Location.MARS, g1, red, g2, "evey")
    h.run("evey", Location.MARS)
    assert h.state.location(Location.MARS).is_empty
    for cid in (g1, g2, red, "evey"):
        assert cid in h.state.banished
    assert h.state.player("p0").influence_on_institute == 2  # two golds


def test_nero_gains_helium_per_red_here():
    h = Harness()
    r1, r2 = some(Color.RED), some(Color.RED, {some(Color.RED)})
    h.place(Location.MARS, r1, r2, "nero")
    h.run("nero", Location.MARS)
    assert h.state.player("p0").helium == 2


def test_lysander_banishes_self_off_luna():
    h = Harness()
    h.deck(some(Color.RED))
    h.run("lysander", Location.MARS)
    assert "lysander" in h.state.banished
    assert h.state.player("p0").hand  # gained the deck card


def test_lysander_survives_on_luna():
    h = Harness()
    h.deck(some(Color.RED))
    h.run("lysander", Location.LUNA)
    assert "lysander" not in h.state.banished


def test_darrow_gains_non_gold_and_self_banishes_off_gold():
    h = Harness()
    red = some(Color.RED)
    h.place(Location.MARS, red, "darrow")  # deployed on a Red, not a Gold
    h.run("darrow", Location.MARS, red)  # choose to gain the red
    assert red in h.state.player("p0").hand
    assert "darrow" in h.state.banished


def test_pathologist_banishes_bottom_not_itself():
    h = Harness()
    bottom, mid = some(Color.RED), some(Color.BLUE)
    h.place(Location.MARS, bottom, mid, "pathologist")
    h.run("pathologist", Location.MARS)
    assert bottom in h.state.banished
    assert "pathologist" not in h.state.banished


def test_telemanuses_moves_the_substack_in_order():
    h = Harness()
    a, b = some(Color.RED), some(Color.BLUE)
    h.place(Location.MARS, a, b, "telemanuses")  # a (bottom), b, telemanuses (top)
    h.run("telemanuses", Location.MARS, "Jupiter")
    assert h.state.location(Location.MARS).card_ids() == ["telemanuses"]
    assert h.state.location(Location.JUPITER).card_ids() == [a, b]  # order preserved


def test_timony_places_influence_per_gold_at_institute():
    h = Harness()
    g1, g2 = some(Color.GOLD), some(Color.GOLD, {some(Color.GOLD)})
    h.place(Location.INSTITUTE, g1, some(Color.RED), g2)
    h.run("timony", Location.MARS)  # Timony itself deployed elsewhere
    assert h.state.player("p0").influence_on_institute == 2


def test_hacker_can_banish_the_revealed_card():
    h = Harness()
    top = some(Color.RED)
    h.deck(top)
    h.run("hacker", Location.MARS, "banish")
    assert top in h.state.banished


def test_reporter_passes_card_and_ends_turn_when_ahead():
    h = Harness()
    h.state.player("p0").helium = 5  # ahead of p1 (0)
    h.deck(some(Color.RED), some(Color.BLUE))
    h.place(Location.MARS, "reporter")
    ended = h.run("reporter", Location.MARS)
    assert ended is True
    assert "reporter" in h.state.player("p1").hand  # given to the right
    assert len(h.state.player("p0").hand) == 2  # drew 2


def test_reporter_does_nothing_when_not_ahead():
    h = Harness()
    h.place(Location.MARS, "reporter")
    ended = h.run("reporter", Location.MARS)
    assert not ended
    assert "reporter" in h.state.location(Location.MARS).card_ids()


def test_mustang_self_banishes_on_non_gold_pickup():
    h = Harness()
    red = some(Color.RED)
    h.banished(red)
    h.place(Location.MARS, "mustang")
    h.run("mustang", Location.MARS, red)
    assert red in h.state.player("p0").hand
    assert "mustang" in h.state.banished


def test_conversationalist_gains_white_from_another_location():
    h = Harness()
    white = some(Color.WHITE)
    h.place(Location.JUPITER, white)
    h.place(Location.MARS, "conversationalist")
    h.run("conversationalist", Location.MARS, "Jupiter")
    assert white in h.state.player("p0").hand


# --------------------------------------------------------------------------- #
# T3: opponent interaction, steal, blocks, nested turn
# --------------------------------------------------------------------------- #


def test_tactus_steals_the_card_the_victim_gives():
    h = Harness()
    loot = some(Color.RED)
    h.hand("p1", loot, some(Color.BLUE))
    # choose opponent p1, victim gives `loot`, no block available -> stolen
    ended = h.run("tactus", Location.MARS, "p1", loot)
    assert loot in h.state.player("p0").hand
    assert "tactus" in h.state.banished
    assert ended is True


def test_judge_blocks_a_steal():
    h = Harness()
    loot = some(Color.RED, {"judge"})
    h.hand("p1", "judge", loot)
    # p1 gives loot, then reveals Judge to block
    h.run("tactus", Location.MARS, "p1", loot, "block")
    assert loot in h.state.player("p1").hand  # kept
    assert "judge" in h.state.player("p1").hand  # revealed, not banished
    assert "tactus" not in h.state.banished  # steal failed => Tactus not banished


def test_aja_forces_opponent_banish_then_self_banishes():
    h = Harness()
    victim_card = some(Color.RED)
    h.hand("p1", victim_card)
    # sole opponent auto-selected; p1 then picks which of their cards to banish
    h.run("aja", Location.MARS, victim_card)
    assert victim_card in h.state.banished
    assert "aja" in h.state.banished


def test_howlers_blocks_a_forced_banish():
    h = Harness()
    keep = some(Color.RED, {"howlers"})
    h.hand("p1", "howlers", keep)
    h.run("antonia", Location.MARS, "block")
    assert keep in h.state.player("p1").hand
    assert "howlers" in h.state.player("p1").hand  # revealed, stays


def test_justice_blocks_sovereign_theft_and_draws():
    h = Harness()
    h.state.sovereign_holder = "p1"
    h.state.player("p1").has_sovereign = True
    h.hand("p1", "justice")
    h.deck(some(Color.RED))
    # p0 deploys Boneriders to take the Sovereign; p1 blocks with Justice
    h.run("boneriders", Location.LUNA, "block")
    assert h.state.sovereign_holder == "p1"  # kept it
    assert "justice" in h.state.banished  # banished to keep the token
    assert len(h.state.player("p1").hand) == 1  # drew the deck card


def test_auctioneer_opponent_picks_one_actor_gets_the_other_two():
    h = Harness()
    # sole opponent auto-selected; p1 chooses helium, p0 gains fleet + influence
    h.run("auctioneer", Location.MARS, "helium")
    assert h.state.player("p1").helium == 1
    assert h.state.player("p0").fleet == 1
    assert h.state.player("p0").influence_on_institute == 1


def test_quicksilver_steals_helium_from_the_leader():
    h = Harness()
    h.state.player("p1").helium = 4
    h.run("quicksilver", Location.MARS)  # single leader -> no decision
    assert h.state.player("p1").helium == 3
    assert h.state.player("p0").helium == 1


def test_loan_shark_takes_one_helium_when_opponent_cannot_pay():
    h = Harness()
    h.state.player("p1").helium = 1  # cannot afford 2
    h.run("loan-shark", Location.MARS, "p1")
    assert h.state.player("p1").helium == 0
    assert h.state.player("p0").helium == 1


def test_karnus_triggers_opponent_banish_only_on_named_card():
    h = Harness()
    h.place(Location.MARS, "nero", "karnus")  # deployed on Nero (a named trigger)
    victim_card = some(Color.RED, {"nero"})
    h.hand("p1", victim_card)
    h.run("karnus", Location.MARS, "p1", victim_card)
    assert "nero" in h.state.banished  # the card under Karnus
    assert victim_card in h.state.banished  # opponent forced to banish
