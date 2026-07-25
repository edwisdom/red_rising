"""Location bonuses, the Rising die, and house tiles.

Shared by the turn flow (`rules.py`) and by card abilities (`cards/*`) — e.g.
Masseuse grants a location bonus — so it lives here to keep both free of a cycle.
All are generators because several branches ask the player to choose.
"""

from __future__ import annotations

from collections.abc import Generator

from red_rising.enums import DieFace, House, Location

from .context import Ctx
from .decisions import DecisionRequest, Option
from .events import Blocked, HouseAbilityTriggered, LocationBonus

Script = Generator[DecisionRequest, "Option | None"]

ALL_LOCATIONS = tuple(Location)

#: Cards that let their holder keep the Sovereign token when an opponent takes it.
SOVEREIGN_BLOCKERS = ("justice", "martyr")


def gain_sovereign(ctx: Ctx, seat: str) -> Generator[DecisionRequest, Option | None, bool]:
    """Gain (or keep) the Sovereign token. Returns True if `seat` ends up holding it.

    When taking it from an opponent who holds a Justice/Martyr, that opponent may
    reveal-and-banish it to keep the token (and then draws). In that case `seat` does
    not gain it and the caller's house ability does not fire.
    """
    holder = ctx.state.sovereign_holder
    if holder is not None and holder != seat:
        blocker = next((c for c in ctx.hand_of(holder) if c in SOVEREIGN_BLOCKERS), None)
        if blocker is not None:
            choice = yield ctx.choose(
                holder,
                f"An opponent takes the Sovereign — reveal {ctx.card(blocker).name} to keep it?",
                [
                    Option.of_tag("block", f"Banish {ctx.card(blocker).name}, keep token"),
                    Option.of_tag("allow", "Let them take it"),
                ],
                kind="block",
            )
            if choice is not None and choice.tag == "block":
                ctx.banish_from_hand(holder, blocker)
                ctx._emit(Blocked(seat=holder, block_card=blocker, kind="sovereign"))
                ctx.gain_deck_top_to_hand(holder)
                return False
    ctx.set_sovereign(seat)
    return True


def award_location_bonus(ctx: Ctx, seat: str, loc: Location) -> Script:
    ctx._emit(LocationBonus(seat=seat, location=loc))
    match loc:
        case Location.JUPITER:
            ctx.advance_fleet(seat)
        case Location.MARS:
            ctx.gain_helium(seat)
        case Location.LUNA:
            gained = yield from gain_sovereign(ctx, seat)  # gain or keep
            if gained:
                yield from trigger_house_ability(ctx, seat)
        case Location.INSTITUTE:
            ctx.place_influence(seat)


def roll_and_award_die(ctx: Ctx, seat: str) -> Script:
    face = ctx.roll_die(seat)
    yield from apply_die_face(ctx, seat, face)


def apply_die_face(ctx: Ctx, seat: str, face: DieFace) -> Script:
    match face:
        case DieFace.BANISH:
            locs = [loc for loc in ALL_LOCATIONS if not ctx.state.location(loc).is_empty]
            if locs:
                choice = yield ctx.choose_location(
                    seat, "Banish the top card of which location?", locs, kind="die_banish"
                )
                assert choice is not None and choice.location is not None
                ctx.banish_location_top(choice.location)
        case DieFace.REVEAL:
            card_id = ctx.state.draw_from_deck()
            if card_id is not None:
                choice = yield ctx.choose_location(
                    seat, "Place the revealed card where?", ALL_LOCATIONS, kind="die_reveal"
                )
                assert choice is not None and choice.location is not None
                ctx.place_on_location(seat, card_id, choice.location)
        case DieFace.SOVEREIGN:
            gained = yield from gain_sovereign(ctx, seat)
            if gained:
                yield from trigger_house_ability(ctx, seat)
        case DieFace.HELIUM:
            ctx.gain_helium(seat)
        case DieFace.FLEET:
            ctx.advance_fleet(seat)
        case DieFace.INFLUENCE:
            ctx.place_influence(seat)


def trigger_house_ability(ctx: Ctx, seat: str) -> Script:
    """Resolve a house tile, always triggered by (re)gaining the Sovereign token."""
    house = ctx.state.player(seat).house
    ctx._emit(HouseAbilityTriggered(seat=seat, house=house))
    match house:
        case House.MARS:
            ctx.gain_helium(seat)
        case House.JUPITER:
            ctx.advance_fleet(seat)
        case House.DIANA:
            ctx.place_influence(seat)
        case House.APOLLO:
            # Reveal and place (not deploy) the top card of the deck.
            card_id = ctx.state.draw_from_deck()
            if card_id is not None:
                choice = yield ctx.choose_location(
                    seat, "Apollo: place the revealed card where?", ALL_LOCATIONS, kind="apollo"
                )
                assert choice is not None and choice.location is not None
                ctx.place_on_location(seat, card_id, choice.location)
        case House.CERES:
            locs = [loc for loc in ALL_LOCATIONS if not ctx.state.location(loc).is_empty]
            if locs:
                choice = yield ctx.choose_location(
                    seat, "Ceres: banish a card from which location?", locs, kind="ceres"
                )
                assert choice is not None and choice.location is not None
                ctx.banish_location_top(choice.location)
        case House.MINERVA:
            # Roll the die; a Sovereign result is re-chosen as any other bonus so
            # the house ability cannot recurse.
            face = ctx.roll_die(seat)
            if face is DieFace.SOVEREIGN:
                alts = [f for f in DieFace if f is not DieFace.SOVEREIGN]
                choice = yield ctx.choose(
                    seat,
                    "Minerva rolled the Sovereign; choose another bonus",
                    [Option.of_tag(f.value, f.value.title()) for f in alts],
                    kind="minerva",
                )
                assert choice is not None and choice.tag is not None
                face = DieFace(choice.tag)
            yield from apply_die_face(ctx, seat, face)
