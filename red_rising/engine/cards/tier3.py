"""Opponent-interactive deploy abilities.

These prompt an *opponent* mid-resolution. That routing is free: a `DecisionRequest`
carries the seat that must answer, and the engine already surfaces it to exactly
that player (others see "waiting on…"). Steals and forced banishes go through the
block primitives in `abilities.py`, so the Judge/Howlers/Pax defence is automatic.

`loan-shark` is the re-entrancy case: it runs a whole nested turn for the opponent
inside the current one, via the same generator pump.
"""

from __future__ import annotations

from red_rising.enums import Color

from ..abilities import (
    Deploy,
    Script,
    banish_opponent_card,
    choose_opponent,
    confirm,
    deploy,
    force_banish_own_card,
    steal_card,
)
from ..decisions import Option

# --------------------------------------------------------------------------- #
# Force an opponent to banish one of their cards
# --------------------------------------------------------------------------- #


def _choose_then_force_banish(d: Deploy, self_banish: bool) -> Script:
    opp = yield from choose_opponent(d, "Choose an opponent to banish a card")
    if opp is not None:
        yield from force_banish_own_card(d, opp)
    if self_banish:
        d.ctx.banish_card(d.card_id)


@deploy("aja")
def aja(d: Deploy) -> Script:
    """Choose an opponent; they banish 1 of their cards. Then banish Aja."""
    yield from _choose_then_force_banish(d, self_banish=True)


@deploy("antonia")
def antonia(d: Deploy) -> Script:
    """Choose an opponent. They banish 1 of their cards. Then, banish Antonia."""
    yield from _choose_then_force_banish(d, self_banish=True)


@deploy("karnus")
def karnus(d: Deploy) -> Script:
    """Banish the card directly under this one. If the banished card is Mustang, The
    Jackal, or Nero, you may also choose an opponent. If you do, they banish 1 of
    their cards."""
    under = d.under_at_deploy
    if under is None:
        return
    d.ctx.banish_card(under)
    if under in ("mustang", "jackal", "nero"):
        opp = yield from choose_opponent(d, "Also make an opponent banish a card?", optional=True)
        if opp is not None:
            yield from force_banish_own_card(d, opp)


# --------------------------------------------------------------------------- #
# Steal
# --------------------------------------------------------------------------- #


@deploy("tactus")
def tactus(d: Deploy) -> Script:
    """You may steal 1 card from an opponent (they choose the card). If you do, banish
    Tactus and end your turn."""
    opp = yield from choose_opponent(d, "Steal from which opponent?", optional=True)
    if opp is None:
        return
    hand = d.ctx.hand_of(opp)
    if not hand:
        return
    # The victim chooses which card they give up.
    choice = yield d.ctx.choose_card(opp, "Give a card to your opponent", list(hand), kind="give")
    given = choice.card_id if choice else hand[0]
    if (yield from steal_card(d, opp, given)):
        d.ctx.banish_card(d.card_id)
        d.end_turn()


@deploy("roque")
def roque(d: Deploy) -> Script:
    """Look at an opponent's hand, name a card, then randomly select a card from their
    hand. If you select the named card, banish it and banish Roque."""
    opp = yield from choose_opponent(d, "Look at whose hand?")
    if opp is None:
        return
    hand = d.ctx.hand_of(opp)
    if not hand:
        return
    # You see their hand and name a card; a random card is then drawn.
    named = yield d.ctx.choose_card(d.seat, "Name a card in their hand", list(hand), kind="name")
    picked = d.ctx.rng.choice(list(hand))
    hit = named is not None and picked == named.card_id
    if hit and (yield from banish_opponent_card(d, opp, picked)):
        d.ctx.banish_card(d.card_id)


# --------------------------------------------------------------------------- #
# Opponent loses a resource (not a card => no block)
# --------------------------------------------------------------------------- #


@deploy("harmony")
def harmony(d: Deploy) -> Script:
    """An opponent of your choice loses 1 Helium."""
    opp = yield from choose_opponent(d, "Which opponent loses 1 Helium?")
    if opp is not None:
        d.ctx.lose_helium(opp)


@deploy("quicksilver")
def quicksilver(d: Deploy) -> Script:
    """Steal 1 Helium from the opponent with the most Helium (if tied, you choose)."""
    opps = d.ctx.opponents(d.seat)
    most = max((o.helium for o in opps), default=0)
    if most <= 0:
        return
    leaders = [o.seat for o in opps if o.helium == most]
    if len(leaders) == 1:
        victim = leaders[0]
    else:
        names = {o.seat: o.name for o in opps}
        choice = yield d.ctx.choose(
            d.seat,
            "Steal Helium from which leader?",
            [Option.of_seat(s, names[s]) for s in leaders],
        )
        victim = choice.seat if choice else leaders[0]
    assert victim is not None
    d.ctx.lose_helium(victim)
    d.ctx.gain_helium(d.seat)


@deploy("eo")
def eo(d: Deploy) -> None:
    """Each opponent must reveal a Red. If they can't, they lose 1 Helium."""
    for opp in d.ctx.opponents(d.seat):
        if d.ctx.count_in_hand(opp.seat, Color.RED) == 0:
            d.ctx.lose_helium(opp.seat)


@deploy("arlus")
def arlus(d: Deploy) -> Script:
    """Each neighboring player reveals a random card from their hand. If it is Gold,
    banish that card. If it is Red, banish Arlus."""
    for opp in d.ctx.opponents(d.seat):  # 2p: the single neighbour
        hand = d.ctx.hand_of(opp.seat)
        if not hand:
            continue
        card = d.ctx.rng.choice(list(hand))
        color = d.ctx.color(card)
        if color is Color.GOLD:
            yield from banish_opponent_card(d, opp.seat, card)
        elif color is Color.RED:
            d.ctx.banish_card(d.card_id)


# --------------------------------------------------------------------------- #
# Opponent makes a choice that benefits you
# --------------------------------------------------------------------------- #


@deploy("auctioneer")
def auctioneer(d: Deploy) -> Script:
    """Choose an opponent. That opponent chooses one: Gain 1 Helium, advance on the
    Fleet Track, or place 1 Influence. You gain both other options."""
    opp = yield from choose_opponent(d, "Which opponent chooses?")
    if opp is None:
        return
    kinds = ["helium", "fleet", "influence"]
    choice = yield d.ctx.choose(
        opp,
        "Choose your bonus (your opponent gains the other two)",
        [Option.of_tag(k, k.title()) for k in kinds],
    )
    theirs = choice.tag if choice else kinds[0]
    _grant(d, opp, theirs)
    for k in kinds:
        if k != theirs:
            _grant(d, d.seat, k)


def _grant(d: Deploy, seat: str, kind: str) -> None:
    if kind == "helium":
        d.ctx.gain_helium(seat)
    elif kind == "fleet":
        d.ctx.advance_fleet(seat)
    else:
        d.ctx.place_influence(seat)


@deploy("diplomat")
def diplomat(d: Deploy) -> Script:
    """You and an opponent of your choice may place 1 Influence on the Institute."""
    d.ctx.place_influence(d.seat)
    opp = yield from choose_opponent(d, "Which opponent may also place 1 Influence?", optional=True)
    if opp is not None and (yield from confirm(d, "Place 1 Influence for them?", seat=opp)):
        d.ctx.place_influence(opp)


@deploy("hypnotist")
def hypnotist(d: Deploy) -> Script:
    """In clockwise order starting with you, each player selects a card from their
    hand, banishes it, and gains the top card of the deck."""
    players = d.state.players
    start = next(i for i, p in enumerate(players) if p.seat == d.seat)
    order = [players[(start + k) % len(players)].seat for k in range(len(players))]
    for seat in order:
        hand = d.ctx.hand_of(seat)
        if hand:
            choice = yield d.ctx.choose_card(
                seat, "Banish a card, then draw", list(hand), kind="hypnotist"
            )
            d.ctx.banish_from_hand(seat, choice.card_id if choice else hand[0])
        d.ctx.gain_deck_top_to_hand(seat)


# --------------------------------------------------------------------------- #
# Loan Shark — a nested turn for the opponent inside yours
# --------------------------------------------------------------------------- #


@deploy("loan-shark")
def loan_shark(d: Deploy) -> Script:
    """Choose an opponent. They may give you 2 Helium to immediately take 1 turn out
    of order (but may not gain Loan Shark) before you finish your turn. Otherwise they
    must give you 1 Helium."""
    opp = yield from choose_opponent(d, "Choose an opponent for Loan Shark")
    if opp is None:
        return
    can_pay = d.state.player(opp).helium >= 2
    take_turn = can_pay and (yield from confirm(d, "Pay 2 Helium to take a turn now?", seat=opp))
    if take_turn:
        d.ctx.lose_helium(opp, 2)
        d.ctx.gain_helium(d.seat, 2)
        # A full nested turn for the opponent, driven by the same pump.
        from ..rules import play_turn  # local import avoids a module-load cycle

        yield from play_turn(d.ctx, opp)
    else:
        d.ctx.lose_helium(opp, 1)
        d.ctx.gain_helium(d.seat, 1)
