"""Player-choice deploy abilities that touch only your own resources and the board
(no opponent interaction — that is `tier3`).

Several large families share a helper:
* **grab** — "You may gain a <thing> from this location; if you do, end your turn."
* **magnet** — "Move a <colors> from any location to under this card; you may gain it."
* **reveal-2-under** — "If deployed on <loc>, reveal the top 2 and place them under
  this card."
"""

from __future__ import annotations

from red_rising.enums import Color, Location

from ..abilities import (
    Deploy,
    Script,
    cards_at,
    choose_card,
    choose_color,
    choose_location,
    confirm,
    deploy,
)

ALL = tuple(Location)


# --------------------------------------------------------------------------- #
# Family: "You may gain <X> from this location. If you do, end your turn."
# --------------------------------------------------------------------------- #


def _grab(
    d: Deploy,
    *,
    colors: tuple[Color, ...] | None = None,
    ids: tuple[str, ...] | None = None,
    prompt: str,
    pay_helium: int = 0,
    banish_self: bool = False,
) -> Script:
    elig = cards_at(d, d.location, exclude=(d.card_id,), colors=colors)
    if ids is not None:
        elig = [c for c in elig if c in ids]
    if pay_helium and d.state.player(d.seat).helium < pay_helium:
        elig = []
    chosen = yield from choose_card(d, prompt, elig, optional=True)
    if chosen is None:
        return
    if pay_helium:
        d.ctx.lose_helium(d.seat, pay_helium)
    d.ctx.gain_card_from_location(d.seat, chosen)
    if banish_self:
        d.ctx.banish_card(d.card_id)
    d.end_turn()


@deploy("aegis-craftsman")
def aegis_craftsman(d: Deploy) -> Script:
    """You may gain a Gold from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.GOLD,), prompt="Gain a Gold from here?")


@deploy("razor-designer")
def razor_designer(d: Deploy) -> Script:
    """You may gain a Gold from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.GOLD,), prompt="Gain a Gold from here?")


@deploy("cyther")
def cyther(d: Deploy) -> Script:
    """You may gain a Blue from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.BLUE,), prompt="Gain a Blue from here?")


@deploy("pulse-armorer")
def pulse_armorer(d: Deploy) -> Script:
    """You may gain a Gray from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.GRAY,), prompt="Gain a Gray from here?")


@deploy("pulse-fistengineer")
def pulse_fistengineer(d: Deploy) -> Script:
    """You may gain an Obsidian from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.OBSIDIAN,), prompt="Gain an Obsidian from here?")


@deploy("gravboot-cobbler")
def gravboot_cobbler(d: Deploy) -> Script:
    """You may gain a Gold or Gray from this location. If you do, end your turn."""
    yield from _grab(d, colors=(Color.GOLD, Color.GRAY), prompt="Gain a Gold or Gray from here?")


@deploy("artificer")
def artificer(d: Deploy) -> Script:
    """You may gain a Gold or any other Orange from this location. If you do, end
    your turn."""
    yield from _grab(
        d, colors=(Color.GOLD, Color.ORANGE), prompt="Gain a Gold or Orange from here?"
    )


@deploy("developer")
def developer(d: Deploy) -> Script:
    """You may gain any other card from this location. If you do, end your turn."""
    yield from _grab(d, prompt="Gain any card from here?")


@deploy("banker")
def banker(d: Deploy) -> Script:
    """You may pay 3 Helium to gain any card from this location. If you do, banish
    Banker."""
    yield from _grab(
        d, prompt="Pay 3 Helium to gain a card from here?", pay_helium=3, banish_self=True
    )


@deploy("alfrun")
def alfrun(d: Deploy) -> Script:
    """You may gain Nero or Jopho from this location. If you do, regain Alfrun and
    end your turn."""
    yield from _grab_and_regain(d, ("nero", "jopho"), "Gain Nero or Jopho from here?")


@deploy("jopho")
def jopho(d: Deploy) -> Script:
    """You may gain Alfrun or Nero from this location. If you do, regain Jopho and
    end your turn."""
    yield from _grab_and_regain(d, ("alfrun", "nero"), "Gain Alfrun or Nero from here?")


def _grab_and_regain(d: Deploy, ids: tuple[str, ...], prompt: str) -> Script:
    elig = [c for c in cards_at(d, d.location, exclude=(d.card_id,)) if c in ids]
    chosen = yield from choose_card(d, prompt, elig, optional=True)
    if chosen is None:
        return
    d.ctx.gain_card_from_location(d.seat, chosen)
    d.ctx.regain_to_hand(d.seat, d.card_id)  # "regain" the source back to hand
    d.end_turn()


# --------------------------------------------------------------------------- #
# Family: magnet — move a coloured card under this card, may gain it
# --------------------------------------------------------------------------- #


def _magnet(d: Deploy, colors: tuple[Color, ...]) -> Script:
    elig = [cid for loc in ALL for cid in cards_at(d, loc, exclude=(d.card_id,), colors=colors)]
    chosen = yield from choose_card(d, "Move which card under this card?", elig)
    if chosen is None:
        return
    d.ctx.move_card(chosen, d.location, under=d.card_id)
    if (yield from confirm(d, f"Gain {d.ctx.card(chosen).name}?")):
        d.ctx.gain_card_from_location(d.seat, chosen)
        d.end_turn()


@deploy("bridge")
def bridge(d: Deploy) -> Script:
    """Move a Pink or Violet from any location to directly under this card. You may
    gain that card; if you do, end your turn."""
    yield from _magnet(d, (Color.PINK, Color.VIOLET))


@deploy("colonel-valentin")
def colonel_valentin(d: Deploy) -> Script:
    """Move a Gold from any location to directly under this card. You may gain that
    card; if you do, end your turn."""
    yield from _magnet(d, (Color.GOLD,))


@deploy("danto")
def danto(d: Deploy) -> Script:
    """Move a Copper or White from any location to directly under this card. You may
    gain that card; if you do, end your turn."""
    yield from _magnet(d, (Color.COPPER, Color.WHITE))


@deploy("holiday")
def holiday(d: Deploy) -> Script:
    """Move an Orange or Blue from any location to directly under this card. You may
    gain that card; if you do, end your turn."""
    yield from _magnet(d, (Color.ORANGE, Color.BLUE))


@deploy("sun-hwa")
def sun_hwa(d: Deploy) -> Script:
    """Move an Obsidian or Green from any location to directly under this card. You
    may gain that card; if you do, end your turn."""
    yield from _magnet(d, (Color.OBSIDIAN, Color.GREEN))


@deploy("trigg")
def trigg(d: Deploy) -> Script:
    """Move a Gray or Yellow from any location to under this card. You may gain that
    card; if you do, end your turn."""
    yield from _magnet(d, (Color.GRAY, Color.YELLOW))


@deploy("ugly-dan")
def ugly_dan(d: Deploy) -> Script:
    """Move a Red or Brown from any location to under this card. You may gain that
    card; if you do, end your turn."""
    yield from _magnet(d, (Color.RED, Color.BROWN))


# --------------------------------------------------------------------------- #
# Family: "If deployed on <loc>, reveal top 2 and place under this card"
# --------------------------------------------------------------------------- #


def _reveal2_under(d: Deploy, loc: Location) -> None:
    if d.location is not loc:
        return
    for _ in range(2):
        cid = d.ctx.reveal_deck_top()
        if cid is None:
            break
        d.ctx.place_under(d.seat, cid, d.card_id, d.location)


@deploy("administrator")
def administrator(d: Deploy) -> None:
    """If deployed on the Institute, reveal the top 2 cards of the deck and place them
    under this card in any order."""
    _reveal2_under(d, Location.INSTITUTE)


@deploy("dataport-specialist")
def dataport_specialist(d: Deploy) -> None:
    """If deployed on Jupiter, reveal the top 2 cards of the deck and place them under
    this card in any order."""
    _reveal2_under(d, Location.JUPITER)


@deploy("dr.-virany")
def dr_virany(d: Deploy) -> None:
    """If deployed on Mars, reveal the top 2 cards of the deck and place them under
    this card in any order."""
    _reveal2_under(d, Location.MARS)


@deploy("holo-designer")
def holo_designer(d: Deploy) -> None:
    """If deployed on Luna, reveal the top 2 cards of the deck and place them under
    this card in any order."""
    _reveal2_under(d, Location.LUNA)


# --------------------------------------------------------------------------- #
# Silver economy (pay / trade)
# --------------------------------------------------------------------------- #


@deploy("ceo")
def ceo(d: Deploy) -> Script:
    """You may regress once on the Fleet Track. If you do, gain 2 Helium."""
    if d.state.player(d.seat).fleet == 0:
        return
    if (yield from confirm(d, "Regress 1 on the Fleet Track to gain 2 Helium?")):
        d.ctx.regress_fleet(d.seat)
        d.ctx.gain_helium(d.seat, 2)


@deploy("sponsor")
def sponsor(d: Deploy) -> Script:
    """You may pay 1 Helium to place 2 Influence on the Institute."""
    if d.state.player(d.seat).helium < 1:
        return
    if (yield from confirm(d, "Pay 1 Helium to place 2 Influence?")):
        d.ctx.lose_helium(d.seat)
        d.ctx.place_influence(d.seat, 2)


@deploy("stock-broker")
def stock_broker(d: Deploy) -> Script:
    """You may lose 1 Influence from the Institute. If you do, gain 2 Helium."""
    if d.state.player(d.seat).influence_on_institute < 1:
        return
    if (yield from confirm(d, "Return 1 Influence from the Institute to gain 2 Helium?")):
        d.ctx.remove_influence(d.seat)
        d.ctx.gain_helium(d.seat, 2)


@deploy("politician")
def politician(d: Deploy) -> Script:
    """You may reveal 2 Golds from your hand. If you do, place 2 Influence on the
    Institute."""
    if d.ctx.count_in_hand(d.seat, Color.GOLD) < 2:
        return
    if (yield from confirm(d, "Reveal 2 Golds to place 2 Influence?")):
        d.ctx.place_influence(d.seat, 2)


@deploy("surgeon")
def surgeon(d: Deploy) -> Script:
    """You may banish a non-Gold from your hand and gain a banished Gold."""
    hand_non_gold = [c for c in d.ctx.hand_of(d.seat) if not d.ctx.is_gold(c)]
    banished_golds = [c for c in d.state.banished if d.ctx.is_gold(c)]
    if not hand_non_gold or not banished_golds:
        return
    to_banish = yield from choose_card(
        d, "Banish which non-Gold from your hand?", hand_non_gold, optional=True
    )
    if to_banish is None:
        return
    to_gain = yield from choose_card(d, "Gain which banished Gold?", banished_golds)
    d.ctx.banish_from_hand(d.seat, to_banish)
    if to_gain is not None:
        d.ctx.gain_banished(d.seat, to_gain)


@deploy("investor")
def investor(d: Deploy) -> Script:
    """Choose a color other than Silver. Gain 1 Helium for each card of that color at
    this location."""
    color = yield from choose_color(
        d, "Name a color (not Silver)", [c for c in Color if c is not Color.SILVER]
    )
    if color is None:
        return
    n = len(cards_at(d, d.location, exclude=(d.card_id,), colors=(color,)))
    if n:
        d.ctx.gain_helium(d.seat, n)


# --------------------------------------------------------------------------- #
# Deck manipulation
# --------------------------------------------------------------------------- #


@deploy("firewall-expert")
def firewall_expert(d: Deploy) -> Script:
    """Look at the top 3 cards of the deck. Place 1 of them face down at the top of
    each location. (Colorless while face down.)"""
    revealed = [c for c in (d.ctx.reveal_deck_top() for _ in range(3)) if c is not None]
    used: set[Location] = set()
    for cid in revealed:
        locs = [loc for loc in ALL if loc not in used]
        dest = yield from choose_location(d, "Place a face-down card on which location?", locs)
        if dest is None:
            dest = locs[0]
        d.ctx.place_on_location(d.seat, cid, dest, face_down=True)
        used.add(dest)


@deploy("psychologist")
def psychologist(d: Deploy) -> Script:
    """You may place (not deploy) 1 or 2 banished cards on the top of one location."""
    if not d.state.banished:
        return
    dest = yield from choose_location(d, "Place banished cards on which location?", list(ALL))
    if dest is None:
        return
    for i in range(2):
        opts = list(d.state.banished)
        if not opts:
            break
        picked = yield from choose_card(
            d, f"Place banished card #{i + 1} (optional)", opts, optional=True
        )
        if picked is None:
            break
        d.ctx.take_banished(picked)
        d.ctx.place_on_location(d.seat, picked, dest)


@deploy("group-counselor")
def group_counselor(d: Deploy) -> Script:
    """Choose up to 3 banished cards and place each of them either on the top or
    bottom of the deck."""
    for i in range(3):
        opts = list(d.state.banished)
        if not opts:
            break
        picked = yield from choose_card(
            d, f"Move banished card #{i + 1} to the deck (optional)", opts, optional=True
        )
        if picked is None:
            break
        top = yield from confirm(
            d, f"Place {d.ctx.card(picked).name} on TOP of the deck? (No = bottom)"
        )
        d.ctx.take_banished(picked)
        d.ctx.put_on_deck(picked, top=top)


@deploy("mickey-the-carver")
def mickey_the_carver(d: Deploy) -> Script:
    """You may banish a Red from your hand. If you do, reveal cards from the deck
    until you find a Gold. Gain it and place the revealed cards at the bottom of the
    deck in any order."""
    reds = [c for c in d.ctx.hand_of(d.seat) if d.ctx.color(c) is Color.RED]
    if not reds:
        return
    to_banish = yield from choose_card(d, "Banish which Red from your hand?", reds, optional=True)
    if to_banish is None:
        return
    d.ctx.banish_from_hand(d.seat, to_banish)
    non_gold: list[str] = []
    while True:
        cid = d.ctx.reveal_deck_top()
        if cid is None:
            break
        if d.ctx.is_gold(cid):
            d.ctx.card_to_hand(d.seat, cid)
            break
        non_gold.append(cid)
    for cid in non_gold:  # returned to the bottom
        d.ctx.put_on_deck(cid, top=False)


@deploy("online-gambler")
def online_gambler(d: Deploy) -> Script:
    """Name 3 colors, then reveal the top card of the deck. If it matches a color you
    named, gain it and banish this card. Otherwise, banish the revealed card."""
    named: list[Color] = []
    remaining = list(Color)
    for i in range(3):
        c = yield from choose_color(d, f"Name color #{i + 1}", remaining)
        if c is None:
            break
        named.append(c)
        remaining.remove(c)
    revealed = d.ctx.reveal_deck_top()
    if revealed is None:
        return
    if d.ctx.color(revealed) in named:
        d.ctx.card_to_hand(d.seat, revealed)
        d.ctx.banish_card(d.card_id)
    else:
        d.ctx.banish_deck_card(d.seat, revealed)


# --------------------------------------------------------------------------- #
# Special
# --------------------------------------------------------------------------- #


@deploy("sevro")
def sevro(d: Deploy) -> Script:
    """Banish the card directly under this one. You may reveal The Howlers to instead
    gain that card."""
    under = d.under_at_deploy
    if under is None:
        return
    has_howlers = "howlers" in d.ctx.hand_of(d.seat)
    if has_howlers and (yield from confirm(d, "Reveal The Howlers to gain that card instead?")):
        d.ctx.gain_card_from_location(d.seat, under)
        return
    d.ctx.banish_card(under)


@deploy("theodora")
def theodora(d: Deploy) -> Script:
    """You may move the bottom card of this location on top of this card. If it's a
    Gold or Red, gain it, then end your turn."""
    bottom = d.this_stack().bottom()
    if bottom is None or bottom.card_id == d.card_id:
        return
    b = bottom.card_id
    if not (yield from confirm(d, f"Move the bottom card ({d.ctx.card(b).name}) on top?")):
        return
    d.ctx.move_card(b, d.location)  # bottom -> top of this location
    if d.ctx.color(b) in (Color.GOLD, Color.RED):
        d.ctx.gain_card_from_location(d.seat, b)
        d.end_turn()
