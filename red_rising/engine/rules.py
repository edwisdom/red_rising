"""Game rules expressed as scripts over a `Ctx`.

The turn flow is a generator: it `yield`s a `DecisionRequest` whenever the active
player (or, later, an opponent) must choose, and runs mechanical steps in between.
The engine pumps it. From Phase 3, card deploy abilities become nested scripts
invoked with `yield from` at the point of deploy — the machinery here does not
change.

Nothing in this module reads the clock or does I/O; all randomness goes through
`ctx.rng` / `ctx.roll_die` so games are reproducible from their seed.
"""

from __future__ import annotations

from collections.abc import Generator

from red_rising.carddefs import load_cards
from red_rising.enums import (
    CARDS_PER_LOCATION_AT_SETUP,
    END_THRESHOLD,
    STARTING_HAND,
    House,
    Location,
)

# Importing the card packages registers every deploy script into the ability
# registry that `trigger_deploy` consults.
from . import cards as _cards  # noqa: E402,F401  (import for registration side effect)
from .abilities import trigger_deploy
from .bonuses import award_location_bonus, roll_and_award_die
from .context import Ctx
from .decisions import DecisionRequest, Option
from .events import (
    CardDealt,
    CardsToLocation,
    GameEndTriggered,
)
from .state import GameState, LocationStack, PlayerState

# A script yields decision requests and is sent back the chosen Option (or None
# when an optional decision is skipped). It returns nothing meaningful.
Script = Generator[DecisionRequest, "Option | None"]

ALL_LOCATIONS = tuple(Location)


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #


def setup_game(
    state: GameState,
    rng,
    emit,
    houses: dict[str, House],
) -> None:
    """Deal the opening position. Mutates `state`, emits setup events.

    Assumes `state.players` are already seated (seat ids, names) and rotated so
    the first player is index 0. `houses` maps seat -> House.
    """
    cards = load_cards()
    state.deck = [c.id for c in cards]
    rng.shuffle(state.deck)

    state.locations = {loc: LocationStack(location=loc) for loc in ALL_LOCATIONS}
    for loc in ALL_LOCATIONS:
        placed: list[str] = []
        for _ in range(CARDS_PER_LOCATION_AT_SETUP):
            card_id = state.draw_from_deck()
            if card_id is None:
                break
            state.location(loc).place_on_top(card_id)
            placed.append(card_id)
        emit(CardsToLocation(location=loc, card_ids=tuple(placed)))

    for player in state.players:
        # House Ceres begins with +1 card.
        count = STARTING_HAND + (1 if houses[player.seat] is House.CERES else 0)
        for _ in range(count):
            card_id = state.draw_from_deck()
            if card_id is None:
                break
            player.hand.append(card_id)
            emit(CardDealt(seat=player.seat, card_id=card_id))

    # 2-player: a neutral house seeds 3 Influence on the Institute for scoring.
    if len(state.players) == 2:
        state.neutral_influence = 3


# --------------------------------------------------------------------------- #
# A turn
# --------------------------------------------------------------------------- #


def play_turn(ctx: Ctx, seat: str) -> Script:
    """One full turn for `seat`: choose Lead or Scout, resolve it."""
    from .events import ActionChosen

    options = [Option.of_tag("lead", "Lead")]
    if ctx.state.deck:
        options.append(Option.of_tag("scout", "Scout"))
    choice = yield ctx.choose(seat, "Choose your action", options, kind="action")
    action = choice.tag if choice else "lead"
    ctx._emit(ActionChosen(seat=seat, action=action))  # type: ignore[arg-type]

    if action == "scout":
        yield from _scout(ctx, seat)
    else:
        yield from _lead(ctx, seat)


def _lead(ctx: Ctx, seat: str) -> Script:
    deployed_to: Location | None = None
    hand = ctx.hand_of(seat)

    # 1. Deploy a card from hand (skipped if the hand is empty). In Phase 1 the
    #    deploy ability is not triggered — that is Phase 3.
    if hand:
        card_choice = yield ctx.choose_card(seat, "Deploy a card", list(hand), kind="deploy")
        assert card_choice is not None
        loc_choice = yield ctx.choose_location(
            seat, f"Deploy {card_choice.card_id} where?", ALL_LOCATIONS, kind="deploy_to"
        )
        assert loc_choice is not None and loc_choice.location is not None
        deployed_to = loc_choice.location
        ctx.deploy_from_hand(seat, card_choice.card_id, deployed_to)

        # Trigger the deployed card's ability. Some abilities end the turn early,
        # in which case the Lead's completion step is skipped.
        ended = yield from trigger_deploy(ctx, seat, card_choice.card_id, deployed_to)
        if ended:
            return

    # 2. Complete the Lead: gain from a location you didn't deploy to (+ its bonus),
    #    or from the deck (then roll the die for a bonus).
    completions: list[Option] = []
    for loc in ALL_LOCATIONS:
        if loc is deployed_to:
            continue
        if not ctx.state.location(loc).is_empty:
            completions.append(Option.of_location(loc, f"Gain top of {loc.display}"))
    if ctx.state.deck:
        completions.append(Option.of_tag("deck", "Gain top of deck (roll die)"))

    if not completions:
        return  # nothing to gain; turn ends after the deploy

    completion = yield ctx.choose(seat, "Complete your Lead", completions, kind="complete")
    assert completion is not None
    if completion.location is not None:
        ctx.gain_location_top_to_hand(seat, completion.location)
        yield from award_location_bonus(ctx, seat, completion.location)
    else:
        ctx.gain_deck_top_to_hand(seat)
        yield from roll_and_award_die(ctx, seat)


def _scout(ctx: Ctx, seat: str) -> Script:
    """Reveal the top of the deck, place it on a location, gain that location's bonus."""
    card_id = ctx.state.draw_from_deck()
    if card_id is None:
        return
    loc_choice = yield ctx.choose_location(
        seat, "Place the revealed card where?", ALL_LOCATIONS, kind="scout_to"
    )
    assert loc_choice is not None and loc_choice.location is not None
    loc = loc_choice.location
    ctx.place_on_location(seat, card_id, loc)
    yield from award_location_bonus(ctx, seat, loc)


# --------------------------------------------------------------------------- #
# Game-end trigger
# --------------------------------------------------------------------------- #


def _meets(player: PlayerState) -> int:
    """How many of the 3 end thresholds this player meets."""
    return sum(
        (
            player.helium >= END_THRESHOLD,
            player.influence_on_institute >= END_THRESHOLD,
            player.fleet >= END_THRESHOLD,
        )
    )


def check_end_trigger(state: GameState, emit, by_seat: str) -> bool:
    """The game ends when all 3 thresholds are met across players, or any 2 by one.

    Returns True the first time the trigger fires. Idempotent afterwards.
    """
    if state.end_triggered_on_turn is not None:
        return False

    any_two_by_one = any(_meets(p) >= 2 for p in state.players)
    all_three_across = (
        any(p.helium >= END_THRESHOLD for p in state.players)
        and any(p.influence_on_institute >= END_THRESHOLD for p in state.players)
        and any(p.fleet >= END_THRESHOLD for p in state.players)
    )
    if any_two_by_one or all_three_across:
        # `turn_number` is the 1-based count of turns begun; store the 0-based index
        # of the turn that just finished, which is what the scheduler reasons about.
        state.end_triggered_on_turn = state.turn_number - 1
        emit(GameEndTriggered(by_seat=by_seat, turn_number=state.turn_number))
        return True
    return False
