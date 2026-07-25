"""Straight-line and simple-conditional deploy abilities.

Each script is written to read against the printed card text (quoted in its
docstring). Plain functions run immediately; generator functions yield a decision
only where the card asks the player to choose.

Deferred to a later tranche: `firewall-expert` (face-down hidden info) belongs with
the harder cards.
"""

from __future__ import annotations

from red_rising.enums import Color, Location

from ..abilities import (
    Deploy,
    Script,
    cards_at,
    choose_card,
    choose_location,
    choose_other_location,
    deploy,
    deploy_card,
    other_locations,
    trigger_deploy,
)
from ..bonuses import award_location_bonus, gain_sovereign, trigger_house_ability
from ..decisions import Option

# --------------------------------------------------------------------------- #
# Pure resources
# --------------------------------------------------------------------------- #


@deploy("deanna")
def deanna(d: Deploy) -> None:
    """Gain 1 Helium."""
    d.ctx.gain_helium(d.seat)


@deploy("uncle-narol")
def uncle_narol(d: Deploy) -> None:
    """Gain 2 Helium."""
    d.ctx.gain_helium(d.seat, 2)


@deploy("lawyer")
def lawyer(d: Deploy) -> None:
    """Place 1 Influence on the Institute."""
    d.ctx.place_influence(d.seat)


def _fleet_wave(d: Deploy) -> None:
    """Advance twice on the Fleet Track, then all other players advance once."""
    d.ctx.advance_fleet(d.seat, 2)
    for opp in d.ctx.opponents(d.seat):
        d.ctx.advance_fleet(opp.seat)


deploy("pelus")(_fleet_wave)
deploy("virga")(_fleet_wave)


# --------------------------------------------------------------------------- #
# "If deployed on <location>, <bonus>"
# --------------------------------------------------------------------------- #


@deploy("invictus")
def invictus(d: Deploy) -> None:
    """If deployed on Mars, advance once on the Fleet Track."""
    if d.location is Location.MARS:
        d.ctx.advance_fleet(d.seat)


@deploy("morning-star")
def morning_star(d: Deploy) -> None:
    """If deployed on Jupiter, advance once on the Fleet Track."""
    if d.location is Location.JUPITER:
        d.ctx.advance_fleet(d.seat)


@deploy("pax")
def pax(d: Deploy) -> None:
    """If deployed on Luna, advance once on the Fleet Track."""
    if d.location is Location.LUNA:
        d.ctx.advance_fleet(d.seat)


@deploy("quietus")
def quietus(d: Deploy) -> None:
    """If deployed on the Institute, advance once on the Fleet Track."""
    if d.location is Location.INSTITUTE:
        d.ctx.advance_fleet(d.seat)


@deploy("fitchner")
def fitchner(d: Deploy) -> None:
    """If deployed to the Institute, place 1 Influence there."""
    if d.location is Location.INSTITUTE:
        d.ctx.place_influence(d.seat)


# --------------------------------------------------------------------------- #
# "If you have the Sovereign token, <bonus>"
# --------------------------------------------------------------------------- #


@deploy("magistrate")
def magistrate(d: Deploy) -> None:
    """If you have the Sovereign token, gain 1 Helium."""
    if d.state.player(d.seat).has_sovereign:
        d.ctx.gain_helium(d.seat)


@deploy("orator")
def orator(d: Deploy) -> None:
    """If you have the Sovereign token, place 1 Influence on the Institute."""
    if d.state.player(d.seat).has_sovereign:
        d.ctx.place_influence(d.seat)


@deploy("priestess")
def priestess(d: Deploy) -> None:
    """If you have the Sovereign token, advance once on the Fleet Track."""
    if d.state.player(d.seat).has_sovereign:
        d.ctx.advance_fleet(d.seat)


@deploy("seer")
def seer(d: Deploy) -> Script:
    """If you have the Sovereign token, reveal the top card of the deck and place
    (not deploy) it on another location."""
    if not d.state.player(d.seat).has_sovereign:
        return
    card_id = d.ctx.reveal_deck_top()
    if card_id is None:
        return
    dest = yield from choose_other_location(d, "Place the revealed card where?")
    if dest is not None:
        d.ctx.place_on_location(d.seat, card_id, dest)


# --------------------------------------------------------------------------- #
# Gaining the Sovereign token (triggers the house tile)
# --------------------------------------------------------------------------- #


def _gain_sovereign(d: Deploy) -> Script:
    """Gain the Sovereign token."""
    gained = yield from gain_sovereign(d.ctx, d.seat)
    if gained:
        yield from trigger_house_ability(d.ctx, d.seat)


deploy("boneriders")(_gain_sovereign)
deploy("jackal")(_gain_sovereign)


# --------------------------------------------------------------------------- #
# "If deployed directly on top of <colors>, move that card ... and <bonus>"
# --------------------------------------------------------------------------- #


def _jump_move(d: Deploy, colors: tuple[Color, ...]) -> Script:
    """If the source was deployed on one of `colors`, move that under-card to another
    location. Returns (via generator return) whether the condition fired."""
    if not d.under_is(*colors):
        return False
    dest = yield from choose_other_location(d, "Move that card to which location?")
    if dest is not None and d.under_at_deploy is not None:
        d.ctx.move_card(d.under_at_deploy, dest)
    return True


@deploy("gardener")
def gardener(d: Deploy) -> Script:
    """If deployed directly on top of a Violet or Pink, move that card to the top of
    another location and gain 1 Helium."""
    if (yield from _jump_move(d, (Color.VIOLET, Color.PINK))):
        d.ctx.gain_helium(d.seat)


@deploy("janitor")
def janitor(d: Deploy) -> Script:
    """If deployed directly on top of a Green, Yellow, or Blue, move that card to the
    top of another location and advance once on the Fleet Track."""
    if (yield from _jump_move(d, (Color.GREEN, Color.YELLOW, Color.BLUE))):
        d.ctx.advance_fleet(d.seat)


@deploy("mess-hall-cook")
def mess_hall_cook(d: Deploy) -> Script:
    """If deployed directly on top of a Gray or Orange, move that card to the top of
    another location and advance once on the Fleet Track."""
    if (yield from _jump_move(d, (Color.GRAY, Color.ORANGE))):
        d.ctx.advance_fleet(d.seat)


@deploy("nanny")
def nanny(d: Deploy) -> Script:
    """If deployed directly on top of a Silver, White, or Copper, move that card to
    the top of another location and gain 1 Helium."""
    if (yield from _jump_move(d, (Color.SILVER, Color.WHITE, Color.COPPER))):
        d.ctx.gain_helium(d.seat)


@deploy("artisan-chef")
def artisan_chef(d: Deploy) -> Script:
    """If deployed directly on top of a Gold, move that Gold to the top of another
    location and place 1 Influence on the Institute."""
    if (yield from _jump_move(d, (Color.GOLD,))):
        d.ctx.place_influence(d.seat)


@deploy("modjob")
def modjob(d: Deploy) -> Script:
    """If deployed directly on top of a Red or Brown, deploy that card to the top of
    another location."""
    if not d.under_is(Color.RED, Color.BROWN) or d.under_at_deploy is None:
        return
    dest = yield from choose_other_location(d, "Deploy that card to which location?")
    if dest is not None:
        yield from deploy_card(d, d.under_at_deploy, dest)


# --------------------------------------------------------------------------- #
# Moving a card off "this location"
# --------------------------------------------------------------------------- #


def _move_by_parity(d: Deploy, even: bool) -> Script:
    cards = [
        cid
        for cid in cards_at(d, d.location, exclude=(d.card_id,))
        if (d.ctx.card(cid).core_value % 2 == 0) == even
    ]
    chosen = yield from choose_card(d, "Move which card?", cards)
    if chosen is None:
        return
    dest = yield from choose_other_location(d, "Move it to which location?")
    if dest is not None:
        d.ctx.move_card(chosen, dest)


@deploy("musician")
def musician(d: Deploy) -> Script:
    """Move a card with an even core value from this location to the top of another
    location. (0 is even.)"""
    yield from _move_by_parity(d, even=True)


@deploy("zanzibar")
def zanzibar(d: Deploy) -> Script:
    """Move a card with an odd core value from this location to the top of another
    location."""
    yield from _move_by_parity(d, even=False)


@deploy("4d-painter")
def four_d_painter(d: Deploy) -> Script:
    """Move a card from this location to the top of another location where there are
    no cards with the same color as it."""
    movable = cards_at(d, d.location, exclude=(d.card_id,))
    chosen = yield from choose_card(d, "Move which card?", movable)
    if chosen is None:
        return
    color = d.ctx.color(chosen)
    dests = [
        loc for loc in other_locations(d) if color not in {d.ctx.color(c) for c in cards_at(d, loc)}
    ]
    dest = yield from choose_location(d, "Move it to which location?", dests)
    if dest is not None:
        d.ctx.move_card(chosen, dest)


@deploy("telemanuses")
def telemanuses(d: Deploy) -> Script:
    """Move all cards under this card from this location to the top of another
    location in the same order."""
    stack = d.this_stack()
    idx = stack.index_of(d.card_id)
    under = stack.card_ids()[:idx] if idx else []
    if not under:
        return
    dest = yield from choose_other_location(d, "Move the cards under this to where?")
    if dest is None:
        return
    for cid in under:  # preserve order: bottom-most first
        d.ctx.move_card(cid, dest)


@deploy("masseuse")
def masseuse(d: Deploy) -> Script:
    """Move the top card of another location to the top of a different location. Gain
    the original location bonus for that card."""
    sources = other_locations(d, nonempty=True)
    src = yield from choose_location(d, "Move the top card of which location?", sources)
    if src is None:
        return
    top = d.state.location(src).top()
    assert top is not None
    dests = [loc for loc in Location if loc is not src]
    dest = yield from choose_location(d, "Move it to which location?", dests)
    if dest is None:
        return
    d.ctx.move_card(top.card_id, dest)
    yield from award_location_bonus(d.ctx, d.seat, src)


@deploy("orion")
def orion(d: Deploy) -> Script:
    """If this is deployed on Mars, Luna, or The Institute, deploy one other Blue from
    this location to Jupiter."""
    if d.location not in (Location.MARS, Location.LUNA, Location.INSTITUTE):
        return
    blues = cards_at(d, d.location, exclude=(d.card_id,), colors=(Color.BLUE,))
    chosen = yield from choose_card(d, "Deploy which Blue to Jupiter?", blues)
    if chosen is not None:
        yield from deploy_card(d, chosen, Location.JUPITER)


@deploy("sefi")
def sefi(d: Deploy) -> Script:
    """Gain another Obsidian from this location."""
    obsidians = cards_at(d, d.location, exclude=(d.card_id,), colors=(Color.OBSIDIAN,))
    chosen = yield from choose_card(d, "Gain which Obsidian?", obsidians)
    if chosen is not None:
        d.ctx.gain_card_from_location(d.seat, chosen)


# --------------------------------------------------------------------------- #
# Banishing on "this location"
# --------------------------------------------------------------------------- #


@deploy("bondilus")
def bondilus(d: Deploy) -> Script:
    """If deployed on Mars, banish 1 non-Gold from this location."""
    if d.location is not Location.MARS:
        return
    non_gold = [c for c in cards_at(d, d.location, exclude=(d.card_id,)) if not d.ctx.is_gold(c)]
    chosen = yield from choose_card(d, "Banish which non-Gold?", non_gold)
    if chosen is not None:
        d.ctx.banish_card(chosen)


@deploy("lorn")
def lorn(d: Deploy) -> None:
    """If the card directly under this one is a Gold, banish that card."""
    if d.under_at_deploy is not None and d.ctx.is_gold(d.under_at_deploy):
        d.ctx.banish_card(d.under_at_deploy)


@deploy("pathologist")
def pathologist(d: Deploy) -> None:
    """Banish the bottom card of this location (if it's not this card)."""
    bottom = d.this_stack().bottom()
    if bottom is not None and bottom.card_id != d.card_id:
        d.ctx.banish_card(bottom.card_id)


# --------------------------------------------------------------------------- #
# Deck reveals
# --------------------------------------------------------------------------- #


@deploy("calliope")
def calliope(d: Deploy) -> Script:
    """Reveal the top card of the deck, then deploy it face-up on another location."""
    card_id = d.ctx.reveal_deck_top()
    if card_id is None:
        return
    dest = yield from choose_other_location(d, "Deploy the revealed card where?")
    if dest is None:
        dest = d.location  # nowhere else to go; deploy here
    d.ctx.place_on_location(d.seat, card_id, dest)
    ended = yield from trigger_deploy(d.ctx, d.seat, card_id, dest)
    if ended:
        d.end_turn()


@deploy("hacker")
def hacker(d: Deploy) -> Script:
    """Reveal the top card of the deck. Either banish it or place (not deploy) it to
    the top of another location."""
    card_id = d.ctx.reveal_deck_top()
    if card_id is None:
        return
    opts = [Option.of_tag("banish", "Banish it")]
    opts += [Option.of_location(loc, f"Place on {loc.display}") for loc in other_locations(d)]
    choice = yield d.ctx.choose(d.seat, "Banish or place the revealed card?", opts)
    if choice is None or choice.tag == "banish":
        d.ctx.banish_deck_card(d.seat, card_id)
    else:
        assert choice.location is not None
        d.ctx.place_on_location(d.seat, card_id, choice.location)


@deploy("researcher")
def researcher(d: Deploy) -> None:
    """Place a random banished card at the bottom of this location."""
    if not d.state.banished:
        return
    card_id = d.ctx.rng.choice(d.state.banished)
    d.ctx.place_banished_at_bottom(d.seat, card_id, d.location)


# --------------------------------------------------------------------------- #
# "Give the card to your right-hand neighbour, draw 2, end turn"
# --------------------------------------------------------------------------- #


def _pass_if_ahead(d: Deploy, ahead: bool) -> None:
    """Shared body for Holo Host / Reporter / Vlogger — all fully mechanical."""
    if not ahead:
        return
    right = d.ctx.neighbor_right(d.seat)
    d.ctx.give_location_card_to_hand(d.card_id, right)
    d.ctx.gain_deck_top_to_hand(d.seat)
    d.ctx.gain_deck_top_to_hand(d.seat)
    d.end_turn()


@deploy("holo-host")
def holo_host(d: Deploy) -> None:
    """If you have more Influence on the Institute than the player to your right, give
    them the Holo Host, gain the top 2 cards of the deck, then end your turn."""
    me, right = d.state.player(d.seat), d.state.player(d.ctx.neighbor_right(d.seat))
    _pass_if_ahead(d, me.influence_on_institute > right.influence_on_institute)


@deploy("reporter")
def reporter(d: Deploy) -> None:
    """If you have more Helium than the player to your right, give them the Reporter,
    gain the top 2 cards of the deck, then end your turn."""
    me, right = d.state.player(d.seat), d.state.player(d.ctx.neighbor_right(d.seat))
    _pass_if_ahead(d, me.helium > right.helium)


@deploy("vlogger")
def vlogger(d: Deploy) -> None:
    """If you're further on the Fleet Track than the player to your right, give them
    the Vlogger, gain the top 2 cards of the deck, then end your turn."""
    me, right = d.state.player(d.seat), d.state.player(d.ctx.neighbor_right(d.seat))
    _pass_if_ahead(d, me.fleet > right.fleet)
