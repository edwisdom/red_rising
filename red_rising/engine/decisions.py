"""Decisions: the only way a script asks a player for input.

A running script (the turn flow, and later each card ability) `yield`s a
`DecisionRequest` when it needs a choice. The engine assigns it an id, parks it as
the game's single `pending` decision, and surfaces its enumerated `options` to the
seat that must answer. When an `Answer` arrives, the engine resumes the script with
the chosen option(s).

Because every legal answer is enumerated up front, this same structure serves the
UI (highlight the options), the fuzz tests (pick a random option), and a future
bot (score each option). There is no separate `legal_actions` function — the
pending decision *is* the set of legal moves.
"""

from __future__ import annotations

from pydantic import BaseModel

from red_rising.enums import Location


class Option(BaseModel):
    """One selectable answer. `token` is the stable id the client echoes back.

    The payload fields are a small fixed set covering every choice in the game;
    the yielding code reads whichever it put there. Keeping them explicit (rather
    than an opaque blob) means options serialise cleanly to the client and are
    easy to assert on in tests.
    """

    model_config = {"frozen": True}

    token: str
    label: str
    card_id: str | None = None
    location: Location | None = None
    seat: str | None = None
    tag: str | None = None  # free slot, e.g. "lead" / "scout" / a die face

    @staticmethod
    def of_card(card_id: str, label: str | None = None) -> Option:
        return Option(token=f"card:{card_id}", label=label or card_id, card_id=card_id)

    @staticmethod
    def of_location(loc: Location, label: str | None = None) -> Option:
        return Option(token=f"loc:{loc.value}", label=label or loc.display, location=loc)

    @staticmethod
    def of_seat(seat: str, label: str) -> Option:
        return Option(token=f"seat:{seat}", label=label, seat=seat)

    @staticmethod
    def of_tag(tag: str, label: str | None = None) -> Option:
        return Option(token=f"tag:{tag}", label=label or tag, tag=tag)


class DecisionRequest(BaseModel):
    """What a script yields. The engine fills in `id` when it parks it."""

    model_config = {"frozen": True}

    seat: str  # who must answer
    prompt: str
    options: tuple[Option, ...]
    min_choices: int = 1
    max_choices: int = 1
    kind: str = "choose"  # coarse label for the UI / logs

    def with_id(self, decision_id: int) -> PendingDecision:
        return PendingDecision(id=decision_id, **self.model_dump())


class PendingDecision(DecisionRequest):
    """A `DecisionRequest` that has been assigned an id and is awaiting an answer."""

    id: int

    def option(self, token: str) -> Option | None:
        return next((o for o in self.options if o.token == token), None)


class Answer(BaseModel):
    """A client's response to the current pending decision."""

    decision_id: int
    tokens: tuple[str, ...]  # selected option tokens; length in [min, max]
