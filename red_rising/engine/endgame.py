"""End-of-game (⏰) abilities — scoring step 1.

Resolved after the last turn and before points are tallied, in first-player order.
They gain cards, tokens, or direct points, so they run against the live state and
their effects feed into the final score (and the wildcard optimiser).

The 14 Gray/Orange "treat as…" texts are NOT here — those are the scoring wildcard
mechanic (see `scoring.wildcards`). Artisan Chef's "ignore lost points from Golds"
is a pure scoring modifier, also handled there. This module covers the 11 abilities
that actually *do* something during the end-game step.
"""

from __future__ import annotations

from collections.abc import Callable, Generator

from red_rising.enums import Color, Location

from .context import Ctx
from .decisions import DecisionRequest, Option

Script = Generator[DecisionRequest, "Option | None"]
EndgameFn = Callable[[Ctx, str], "Script | None"]

ENDGAME: dict[str, EndgameFn] = {}


def endgame(card_id: str) -> Callable[[EndgameFn], EndgameFn]:
    def register(fn: EndgameFn) -> EndgameFn:
        ENDGAME[card_id] = fn
        return fn

    return register


def endgame_phase(ctx: Ctx) -> Script:
    """Resolve every player's ⏰ abilities, in first-player order."""
    import inspect

    for player in ctx.state.players:  # players[0] is the first player
        for cid in list(player.hand):
            fn = ENDGAME.get(cid)
            if fn is None:
                continue
            result = fn(ctx, player.seat)
            if inspect.isgenerator(result):
                yield from result


def _yesno(ctx: Ctx, seat: str, prompt: str) -> Generator[DecisionRequest, Option | None, bool]:
    choice = yield ctx.choose(
        seat, prompt, [Option.of_tag("yes", "Yes"), Option.of_tag("no", "No")], kind="endgame"
    )
    return choice is not None and choice.tag == "yes"


# --------------------------------------------------------------------------- #
# Gain a card
# --------------------------------------------------------------------------- #


@endgame("surgeon")
def surgeon(ctx: Ctx, seat: str) -> Script:
    """Gain any 1 banished Gold."""
    golds = [c for c in ctx.state.banished if ctx.is_gold(c)]
    if not golds:
        return
    choice = yield ctx.choose_card(seat, "Surgeon: gain a banished Gold", golds, kind="endgame")
    if choice is not None and choice.card_id is not None:
        ctx.gain_banished(seat, choice.card_id)


@endgame("psychologist")
def psychologist(ctx: Ctx, seat: str) -> None:
    """If you have the fewest cards in hand (ties count), gain 1 random banished card."""
    sizes = [len(p.hand) for p in ctx.state.players]
    if len(ctx.state.player(seat).hand) == min(sizes) and ctx.state.banished:
        ctx.gain_banished(seat, ctx.rng.choice(ctx.state.banished))


@endgame("dr.-virany")
def dr_virany(ctx: Ctx, seat: str) -> Script:
    """You may gain any number of these banished cards: Victra, Sevro, Fitchner, and
    any Reds."""
    while True:
        pool = [
            c
            for c in ctx.state.banished
            if c in ("victra", "sevro", "fitchner") or ctx.color(c) is Color.RED
        ]
        if not pool:
            return
        choice = yield ctx.choose_card(
            seat, "Dr. Virany: gain a banished card (optional)", pool, optional=True, kind="endgame"
        )
        if choice is None or choice.card_id is None:
            return
        ctx.gain_banished(seat, choice.card_id)


def _gain_from_location_if_sovereign(ctx: Ctx, seat: str, loc: Location) -> Script:
    if not ctx.state.player(seat).has_sovereign:
        return
    options = ctx.state.location(loc).card_ids()
    if not options:
        return
    choice = yield ctx.choose_card(seat, f"Gain a card from {loc.display}", options, kind="endgame")
    if choice is not None and choice.card_id is not None:
        ctx.gain_card_from_location(seat, choice.card_id)


@endgame("justice")
def justice(ctx: Ctx, seat: str) -> Script:
    """If you have the Sovereign token, gain 1 card of your choice from Luna."""
    yield from _gain_from_location_if_sovereign(ctx, seat, Location.LUNA)


@endgame("martyr")
def martyr(ctx: Ctx, seat: str) -> Script:
    """If you have the Sovereign token, gain 1 card of your choice from Mars."""
    yield from _gain_from_location_if_sovereign(ctx, seat, Location.MARS)


@endgame("banker")
def banker(ctx: Ctx, seat: str) -> Script:
    """You may pay 3 Helium to gain the top card of any location."""
    if ctx.state.player(seat).helium < 3:
        return
    locs = [loc for loc in Location if not ctx.state.location(loc).is_empty]
    if not locs:
        return
    if not (yield from _yesno(ctx, seat, "Banker: pay 3 Helium to gain a location's top card?")):
        return
    choice = yield ctx.choose_location(seat, "Gain the top card of which location?", locs)
    if choice is not None and choice.location is not None:
        top = ctx.state.location(choice.location).top()
        if top is not None:
            ctx.lose_helium(seat, 3)
            ctx.gain_card_from_location(seat, top.card_id)


@endgame("hypnotist")
def hypnotist(ctx: Ctx, seat: str) -> Script:
    """Banish 1 other card from your hand and gain the top card of the deck."""
    hand = [c for c in ctx.state.player(seat).hand if c != "hypnotist"]
    if hand:
        choice = yield ctx.choose_card(
            seat, "Hypnotist: banish a card, then draw", hand, kind="endgame"
        )
        ctx.banish_from_hand(seat, choice.card_id if choice and choice.card_id else hand[0])
    ctx.gain_deck_top_to_hand(seat)


# --------------------------------------------------------------------------- #
# Gain tokens / points
# --------------------------------------------------------------------------- #


@endgame("auctioneer")
def auctioneer(ctx: Ctx, seat: str) -> Script:
    """Gain 1 Helium, advance once on the Fleet Track, or place 1 Influence."""
    choice = yield ctx.choose(
        seat,
        "Auctioneer (end game): choose a bonus",
        [
            Option.of_tag("helium", "Gain 1 Helium"),
            Option.of_tag("fleet", "Advance Fleet"),
            Option.of_tag("influence", "Place 1 Influence"),
        ],
        kind="endgame",
    )
    tag = choice.tag if choice else "helium"
    if tag == "helium":
        ctx.gain_helium(seat)
    elif tag == "fleet":
        ctx.advance_fleet(seat)
    else:
        ctx.place_influence(seat)


@endgame("investor")
def investor(ctx: Ctx, seat: str) -> Script:
    """Choose a color other than Silver and gain 1 Helium for each card of that color
    on Mars."""
    colors = [c for c in Color if c is not Color.SILVER]
    choice = yield ctx.choose(
        seat,
        "Investor: name a color",
        [Option.of_tag(c.value, c.value) for c in colors],
        kind="endgame",
    )
    if choice is None or choice.tag is None:
        return
    color = Color(choice.tag)
    n = sum(1 for cid in ctx.state.location(Location.MARS).card_ids() if ctx.color(cid) is color)
    if n:
        ctx.gain_helium(seat, n)


@endgame("hacker")
def hacker(ctx: Ctx, seat: str) -> None:
    """Reveal the top card of the deck. Gain points equal to that card's core value."""
    top = ctx.state.peek_deck_top()
    if top is not None:
        ctx.state.player(seat).endgame_points += ctx.card(top).core_value


@endgame("online-gambler")
def online_gambler(ctx: Ctx, seat: str) -> Script:
    """Name 1 non-Gold color. Reveal 7 cards from the top of the deck and gain all
    cards of that color. Return the others to the top of the deck."""
    colors = [c for c in Color if c is not Color.GOLD]
    choice = yield ctx.choose(
        seat,
        "Online Gambler: name a non-Gold color",
        [Option.of_tag(c.value, c.value) for c in colors],
        kind="endgame",
    )
    if choice is None or choice.tag is None:
        return
    color = Color(choice.tag)
    revealed = [c for c in (ctx.reveal_deck_top() for _ in range(7)) if c is not None]
    for cid in revealed:
        if ctx.color(cid) is color:
            ctx.card_to_hand(seat, cid)
        else:
            ctx.put_on_deck(cid, top=True)  # returned to the top
