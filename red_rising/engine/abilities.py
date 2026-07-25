"""The deploy-ability machine: registry, per-card frame, and shared helpers.

A card's deploy ability is a function registered under its id with `@deploy`. It
may be:

* a **plain function** — runs its mechanical effect immediately (no player input), or
* a **generator function** — `yield`s a `DecisionRequest` whenever it needs a choice.

`trigger_deploy` handles both, so a straight-line card reads as straight-line code.
Each script is handed a `Deploy` frame carrying the source card, where it was
deployed, and what sat directly beneath it at deploy time (captured once, so later
moves can't confuse an "if deployed on top of a Gold" check).

Helper generators (`choose_*`, `deploy_card`) express the recurring shapes — "another
location", "a card at this location matching …", "deploy that card too" — so the
individual scripts stay short and legible against the printed text.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Generator
from dataclasses import dataclass, field

from red_rising.enums import Color, Location

from .context import Ctx
from .decisions import DecisionRequest, Option
from .events import Blocked, CardStolen

Script = Generator[DecisionRequest, "Option | None"]
DeployFn = Callable[["Deploy"], "Script | None"]

ALL_LOCATIONS = tuple(Location)

#: card id -> its deploy ability. Populated by @deploy at import time.
REGISTRY: dict[str, DeployFn] = {}


def deploy(card_id: str) -> Callable[[DeployFn], DeployFn]:
    """Register a deploy ability for `card_id`."""

    def register(fn: DeployFn) -> DeployFn:
        if card_id in REGISTRY:
            raise ValueError(f"duplicate deploy script for {card_id}")
        REGISTRY[card_id] = fn
        return fn

    return register


@dataclass
class Deploy:
    """The context handed to a deploy script."""

    ctx: Ctx
    seat: str
    card_id: str  # the card that was just deployed (the "source")
    location: Location  # where it was deployed
    under_at_deploy: str | None  # card directly beneath the source at deploy time
    ended_turn: bool = field(default=False)

    def end_turn(self) -> None:
        self.ended_turn = True

    # Read-through conveniences used constantly by scripts.
    @property
    def state(self):
        return self.ctx.state

    def under_is(self, *colors: Color) -> bool:
        """Was the source deployed directly on top of a card of one of `colors`?"""
        if self.under_at_deploy is None:
            return False
        return self.ctx.color(self.under_at_deploy) in colors

    def this_stack(self):
        return self.state.location(self.location)


def trigger_deploy(ctx: Ctx, seat: str, card_id: str, loc: Location) -> Generator:
    """Run a just-deployed card's ability. Returns whether it ended the turn."""
    fn = REGISTRY.get(card_id)
    if fn is None:
        return False
    under = ctx.state.location(loc).below(card_id)
    frame = Deploy(ctx=ctx, seat=seat, card_id=card_id, location=loc, under_at_deploy=under)
    result = fn(frame)  # plain fns run now; generator fns return a generator
    if inspect.isgenerator(result):
        yield from result
    return frame.ended_turn


# --------------------------------------------------------------------------- #
# Shared decision helpers (generators). Scripts use: x = yield from helper(...)
# --------------------------------------------------------------------------- #


def other_locations(d: Deploy, *, nonempty: bool = False) -> list[Location]:
    locs = [loc for loc in ALL_LOCATIONS if loc is not d.location]
    if nonempty:
        locs = [loc for loc in locs if not d.state.location(loc).is_empty]
    return locs


def choose_other_location(
    d: Deploy, prompt: str, *, nonempty: bool = False
) -> Generator[DecisionRequest, Option | None, Location | None]:
    """Pick a location other than the source's. Auto-resolves when 0/1 candidates."""
    locs = other_locations(d, nonempty=nonempty)
    if not locs:
        return None
    if len(locs) == 1:
        return locs[0]
    choice = yield d.ctx.choose_location(d.seat, prompt, locs)
    return choice.location if choice else None


def choose_location(
    d: Deploy, prompt: str, locs: list[Location]
) -> Generator[DecisionRequest, Option | None, Location | None]:
    if not locs:
        return None
    if len(locs) == 1:
        return locs[0]
    choice = yield d.ctx.choose_location(d.seat, prompt, locs)
    return choice.location if choice else None


def cards_at(
    d: Deploy,
    loc: Location,
    *,
    exclude: tuple[str, ...] = (),
    colors: tuple[Color, ...] | None = None,
) -> list[str]:
    """Face-up card ids at `loc` (face-down cards are colorless and never match a color filter)."""
    out: list[str] = []
    for placed in d.state.location(loc).cards:
        if placed.card_id in exclude or placed.face_down:
            continue
        if colors is not None and d.ctx.color(placed.card_id) not in colors:
            continue
        out.append(placed.card_id)
    return out


def choose_card(
    d: Deploy,
    prompt: str,
    card_ids: list[str],
    *,
    optional: bool = False,
) -> Generator[DecisionRequest, Option | None, str | None]:
    """Pick one of `card_ids`. Auto-resolves a single mandatory candidate."""
    if not card_ids:
        return None
    if len(card_ids) == 1 and not optional:
        return card_ids[0]
    choice = yield d.ctx.choose_card(d.seat, prompt, card_ids, optional=optional)
    return choice.card_id if choice else None


def deploy_card(d: Deploy, card_id: str, to_loc: Location) -> Script:
    """Move `card_id` onto `to_loc` and trigger ITS deploy ability (recursive).

    Used by cards whose text says "deploy that card". Propagates an end-turn signal
    up to the current frame. The Lead's single completion step is unaffected — only
    the outermost `_lead` performs it.
    """
    d.ctx.move_card(card_id, to_loc)
    ended = yield from trigger_deploy(d.ctx, d.seat, card_id, to_loc)
    if ended:
        d.end_turn()


# --------------------------------------------------------------------------- #
# Opponent decisions
# --------------------------------------------------------------------------- #


def confirm(
    d: Deploy, prompt: str, *, seat: str | None = None
) -> Generator[DecisionRequest, Option | None, bool]:
    """A yes/no decision (defaults to the acting seat)."""
    who = seat or d.seat
    choice = yield d.ctx.choose(
        who, prompt, [Option.of_tag("yes", "Yes"), Option.of_tag("no", "No")]
    )
    return choice is not None and choice.tag == "yes"


def choose_color(
    d: Deploy, prompt: str, colors: list[Color]
) -> Generator[DecisionRequest, Option | None, Color | None]:
    if not colors:
        return None
    choice = yield d.ctx.choose(d.seat, prompt, [Option.of_tag(c.value, c.value) for c in colors])
    return Color(choice.tag) if choice and choice.tag else None


def choose_opponent(
    d: Deploy, prompt: str, *, optional: bool = False
) -> Generator[DecisionRequest, Option | None, str | None]:
    """Pick an opponent seat. Auto-resolves when there is exactly one."""
    opps = d.ctx.opponents(d.seat)
    if not opps:
        return None
    if len(opps) == 1 and not optional:
        return opps[0].seat
    choice = yield d.ctx.choose_opponent(d.seat, prompt, optional=optional)
    return choice.seat if choice else None


# --------------------------------------------------------------------------- #
# Block windows (reactive defence). Only these three primitives open a block
# window, so no card script ever has to know blocks exist.
# --------------------------------------------------------------------------- #

#: Reveal-to-block a steal or forced banish of your cards. Card stays in hand.
CARD_BLOCKERS = ("howlers", "judge", "pax-au-telemanus")
#: Reveal-and-banish to keep the Sovereign token, then draw.
SOVEREIGN_BLOCKERS = ("justice", "martyr")


def _held_blocker(ctx: Ctx, seat: str, blockers: tuple[str, ...]) -> str | None:
    return next((c for c in ctx.hand_of(seat) if c in blockers), None)


def _offer_card_block(ctx: Ctx, defender: str) -> Generator[DecisionRequest, Option | None, bool]:
    """Give `defender` the chance to reveal a steal/banish block. True => blocked."""
    blocker = _held_blocker(ctx, defender, CARD_BLOCKERS)
    if blocker is None:
        return False
    choice = yield ctx.choose(
        defender,
        f"An opponent targets your cards — reveal {ctx.card(blocker).name} to block?",
        [
            Option.of_tag("block", f"Reveal {ctx.card(blocker).name}"),
            Option.of_tag("allow", "Allow it"),
        ],
        kind="block",
    )
    if choice is not None and choice.tag == "block":
        ctx._emit(
            Blocked(seat=defender, block_card=blocker, kind="card")
        )  # revealed, stays in hand
        return True
    return False


def steal_card(
    d: Deploy, victim: str, card_id: str
) -> Generator[DecisionRequest, Option | None, bool]:
    """Move `card_id` from `victim`'s hand to the actor's hand, unless blocked."""
    if (yield from _offer_card_block(d.ctx, victim)):
        return False
    d.ctx.state.player(victim).hand.remove(card_id)
    d.ctx.state.player(d.seat).hand.append(card_id)
    d.ctx._emit(CardStolen(from_seat=victim, to_seat=d.seat, card_id=card_id))
    return True


def force_banish_own_card(
    d: Deploy, victim: str
) -> Generator[DecisionRequest, Option | None, bool]:
    """Make `victim` banish one of their own cards (their choice), unless blocked."""
    if not d.ctx.hand_of(victim):
        return False
    if (yield from _offer_card_block(d.ctx, victim)):
        return False
    choice = yield d.ctx.choose_card(
        victim, "Banish one of your cards", list(d.ctx.hand_of(victim)), kind="self_banish"
    )
    target = choice.card_id if choice else d.ctx.hand_of(victim)[0]
    d.ctx.banish_from_hand(victim, target)
    return True


def banish_opponent_card(
    d: Deploy, victim: str, card_id: str
) -> Generator[DecisionRequest, Option | None, bool]:
    """Banish a specific card from `victim`'s hand, unless blocked."""
    if (yield from _offer_card_block(d.ctx, victim)):
        return False
    if card_id in d.ctx.hand_of(victim):
        d.ctx.banish_from_hand(victim, card_id)
        return True
    return False
