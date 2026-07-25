"""Conditional deploy abilities: banish/gain with a follow-up test.

Recurring shape: do something to a card at a location, then key a bonus (or a
self-banish) off what that card was. `d.under_at_deploy` is captured at deploy time,
so "unless you deployed on a Gold" is checked against the true deploy position even
after the ability moves cards around.
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
    other_locations,
)

# --------------------------------------------------------------------------- #
# Banish the card under this one
# --------------------------------------------------------------------------- #


@deploy("assassin")
def assassin(d: Deploy) -> None:
    """Banish the card directly under this one. If it's a Gold, place 1 Influence on
    the Institute."""
    under = d.under_at_deploy
    if under is None:
        return
    was_gold = d.ctx.is_gold(under)
    d.ctx.banish_card(under)
    if was_gold:
        d.ctx.place_influence(d.seat)


@deploy("helga")
def helga(d: Deploy) -> None:
    """Banish the card directly under this one. If it was the only other card on this
    location, gain 1 Helium."""
    under = d.under_at_deploy
    if under is None:
        return
    only_other = len(d.this_stack().cards) == 2  # just the source + that card
    d.ctx.banish_card(under)
    if only_other:
        d.ctx.gain_helium(d.seat)


@deploy("cassius")
def cassius(d: Deploy) -> None:
    """Gain the card directly under this one. Banish Cassius unless that card is a
    Gold."""
    under = d.under_at_deploy
    got_gold = under is not None and d.ctx.is_gold(under)
    if under is not None:
        d.ctx.gain_card_from_location(d.seat, under)
    if not got_gold:
        d.ctx.banish_card(d.card_id)


# --------------------------------------------------------------------------- #
# Banish across locations
# --------------------------------------------------------------------------- #


@deploy("ash-lord")
def ash_lord(d: Deploy) -> None:
    """Banish all Blues from this location. If this banishes 2 or more Blues, regain
    Ash Lord."""
    blues = cards_at(d, d.location, exclude=(d.card_id,), colors=(Color.BLUE,))
    for cid in blues:
        d.ctx.banish_card(cid)
    if len(blues) >= 2:
        d.ctx.regain_to_hand(d.seat, d.card_id)


@deploy("evey")
def evey(d: Deploy) -> None:
    """Banish Evey and all cards at this location. For each Gold banished, place 1
    Influence token on the Institute (max 3)."""
    here = d.this_stack().card_ids()  # includes Evey (the source)
    golds = sum(1 for cid in here if d.ctx.is_gold(cid))
    for cid in list(here):
        d.ctx.banish_card(cid)
    for _ in range(min(3, golds)):
        d.ctx.place_influence(d.seat)


@deploy("alia-snowsparrow")
def alia_snowsparrow(d: Deploy) -> Script:
    """Banish the top non-Gold card from any other location. If it's not Gray or
    Obsidian, gain 1 Helium."""
    locs = [
        loc
        for loc in other_locations(d, nonempty=True)
        if (top := d.state.location(loc).top()) is not None and not d.ctx.is_gold(top.card_id)
    ]

    dest = yield from choose_location(d, "Banish the top card of which location?", locs)
    if dest is None:
        return
    card_id = d.state.location(dest).top().card_id  # type: ignore[union-attr]
    d.ctx.banish_card(card_id)
    if d.ctx.color(card_id) not in (Color.GRAY, Color.OBSIDIAN):
        d.ctx.gain_helium(d.seat)


@deploy("ragnar")
def ragnar(d: Deploy) -> Script:
    """Banish the top card of another location. If it's a Gold or a Gray, place 1
    Influence on the Institute."""

    locs = other_locations(d, nonempty=True)
    dest = yield from choose_location(d, "Banish the top card of which location?", locs)
    if dest is None:
        return
    card_id = d.state.location(dest).top().card_id  # type: ignore[union-attr]
    color = d.ctx.color(card_id)
    d.ctx.banish_card(card_id)
    if color in (Color.GOLD, Color.GRAY):
        d.ctx.place_influence(d.seat)


@deploy("stained")
def stained(d: Deploy) -> Script:
    """Banish any other card from this location. If it's an Obsidian, place 1
    Influence on the Institute."""
    here = cards_at(d, d.location, exclude=(d.card_id,))
    chosen = yield from choose_card(d, "Banish which card?", here)
    if chosen is None:
        return
    was_obsidian = d.ctx.color(chosen) is Color.OBSIDIAN
    d.ctx.banish_card(chosen)
    if was_obsidian:
        d.ctx.place_influence(d.seat)


# --------------------------------------------------------------------------- #
# Gain-then-self-banish Golds
# --------------------------------------------------------------------------- #


@deploy("darrow")
def darrow(d: Deploy) -> Script:
    """Gain any other non-Gold from this location. Banish Darrow unless you deployed
    him on a Gold."""
    non_gold = [c for c in cards_at(d, d.location, exclude=(d.card_id,)) if not d.ctx.is_gold(c)]
    chosen = yield from choose_card(d, "Gain which non-Gold?", non_gold)
    if chosen is not None:
        d.ctx.gain_card_from_location(d.seat, chosen)
    if not d.under_is(Color.GOLD):
        d.ctx.banish_card(d.card_id)


@deploy("romulus")
def romulus(d: Deploy) -> Script:
    """Gain 1 Blue from this location. Banish Romulus unless you deployed him directly
    on top of a Gold."""
    blues = cards_at(d, d.location, exclude=(d.card_id,), colors=(Color.BLUE,))
    chosen = yield from choose_card(d, "Gain which Blue?", blues)
    if chosen is not None:
        d.ctx.gain_card_from_location(d.seat, chosen)
    if not d.under_is(Color.GOLD):
        d.ctx.banish_card(d.card_id)


@deploy("victra")
def victra(d: Deploy) -> None:
    """Gain the bottom card of this location (if it's not this card). Banish Victra
    unless you deployed her on a Gold."""
    bottom = d.this_stack().bottom()
    if bottom is not None and bottom.card_id != d.card_id:
        d.ctx.gain_card_from_location(d.seat, bottom.card_id)
    if not d.under_is(Color.GOLD):
        d.ctx.banish_card(d.card_id)


@deploy("lysander")
def lysander(d: Deploy) -> None:
    """Gain the top card of the deck. Banish Lysander unless you deployed him on
    Luna."""
    d.ctx.gain_deck_top_to_hand(d.seat)
    if d.location is not Location.LUNA:
        d.ctx.banish_card(d.card_id)


@deploy("octavia")
def octavia(d: Deploy) -> None:
    """If you have the Sovereign token, gain the bottom card on Luna (if it's not this
    card); banish Octavia unless that card is a Gold."""
    if not d.state.player(d.seat).has_sovereign:
        return
    bottom = d.state.location(Location.LUNA).bottom()
    bottom_id = bottom.card_id if bottom is not None else None
    if bottom_id is not None and bottom_id != d.card_id:
        d.ctx.gain_card_from_location(d.seat, bottom_id)
    is_gold = bottom_id is not None and d.ctx.is_gold(bottom_id)
    if not is_gold:
        d.ctx.banish_card(d.card_id)


@deploy("mustang")
def mustang(d: Deploy) -> Script:
    """Gain 1 banished card. If that card is not a Gold, banish Mustang."""
    if not d.state.banished:
        return
    chosen = yield from choose_card(d, "Gain which banished card?", list(d.state.banished))
    if chosen is None:
        return
    was_gold = d.ctx.is_gold(chosen)
    d.ctx.gain_banished(d.seat, chosen)
    if not was_gold:
        d.ctx.banish_card(d.card_id)


# --------------------------------------------------------------------------- #
# Move / gain with a colour follow-up
# --------------------------------------------------------------------------- #


@deploy("conversationalist")
def conversationalist(d: Deploy) -> Script:
    """Move the top card from another location to under this card. If it's a White,
    gain it."""
    locs = other_locations(d, nonempty=True)

    src = yield from choose_location(d, "Take the top card of which location?", locs)
    if src is None:
        return
    card_id = d.state.location(src).top().card_id  # type: ignore[union-attr]
    if d.ctx.color(card_id) is Color.WHITE:
        d.ctx.gain_card_from_location(d.seat, card_id)
    else:
        d.ctx.move_card(card_id, d.location, under=d.card_id)


@deploy("garden-trained-rose")
def garden_trained_rose(d: Deploy) -> Script:
    """Move the card directly under this one to the top of another location. If it's a
    Silver, gain 1 Helium."""
    under = d.under_at_deploy
    if under is None:
        return
    dest = yield from choose_other_location(d, "Move that card to which location?")
    if dest is None:
        return
    was_silver = d.ctx.color(under) is Color.SILVER
    d.ctx.move_card(under, dest)
    if was_silver:
        d.ctx.gain_helium(d.seat)


@deploy("matteo")
def matteo(d: Deploy) -> Script:
    """Move any other card from this location to the top of another location. If it's
    a Pink, place 1 Influence token on the Institute."""
    here = cards_at(d, d.location, exclude=(d.card_id,))
    chosen = yield from choose_card(d, "Move which card?", here)
    if chosen is None:
        return
    dest = yield from choose_other_location(d, "Move it to which location?")
    if dest is None:
        return
    was_pink = d.ctx.color(chosen) is Color.PINK
    d.ctx.move_card(chosen, dest)
    if was_pink:
        d.ctx.place_influence(d.seat)


# --------------------------------------------------------------------------- #
# Count-based
# --------------------------------------------------------------------------- #


@deploy("dancer")
def dancer(d: Deploy) -> None:
    """Gain 1 Helium. If you have 2 or more other Reds, reveal them to gain 2 more
    Helium."""
    d.ctx.gain_helium(d.seat)
    if d.ctx.count_in_hand(d.seat, Color.RED) >= 2:
        d.ctx.gain_helium(d.seat, 2)


@deploy("nero")
def nero(d: Deploy) -> None:
    """Gain 1 Helium for each Red at this location."""
    reds = cards_at(d, d.location, exclude=(d.card_id,), colors=(Color.RED,))
    if reds:
        d.ctx.gain_helium(d.seat, len(reds))


@deploy("timony")
def timony(d: Deploy) -> None:
    """For each Gold at the Institute, place 1 influence token there."""
    golds = cards_at(d, Location.INSTITUTE, colors=(Color.GOLD,))
    for _ in golds:
        d.ctx.place_influence(d.seat)


@deploy("codebreaker")
def codebreaker(d: Deploy) -> None:
    """Reveal the bottom card of the deck. If it's a Gold or Silver, leave it there;
    otherwise gain it. Banish Codebreaker unless you deployed it on top of a Gold or
    Silver."""
    bottom = d.ctx.peek_deck_bottom()
    if bottom is not None and d.ctx.color(bottom) not in (Color.GOLD, Color.SILVER):
        d.ctx.take_deck_bottom()
        d.ctx.card_to_hand(d.seat, bottom)
    if not d.under_is(Color.GOLD, Color.SILVER):
        d.ctx.banish_card(d.card_id)
