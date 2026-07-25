"""The engine: drives turn scripts, records events, answers decisions.

Lifecycle:

    engine = Engine.new_game([PlayerSpec(...), ...], seed=42)
    while not engine.finished:
        d = engine.pending            # the one open decision
        engine.answer(Answer(decision_id=d.id, tokens=(d.options[0].token,)))

The engine holds the live turn generator in memory (never serialised). Durability
comes from the event log + turn snapshots (Phase 2): replaying the recorded
`DecisionMade` answers onto a fresh engine reproduces the game exactly, because all
randomness flows through one seeded RNG.
"""

from __future__ import annotations

import random

from pydantic import BaseModel

from red_rising.enums import DieFace, House

from .context import Ctx
from .decisions import Answer, Option, PendingDecision
from .endgame import endgame_phase
from .events import (
    DieRolled,
    Event,
    GameEnded,
    GameStarted,
    TurnBegan,
    TurnEnded,
)
from .rules import Script, check_end_trigger, play_turn, setup_game
from .scoring import ScoreBreakdown, score_game, winners
from .state import GameState, PlayerState


class PlayerSpec(BaseModel):
    name: str
    house: House | None = None  # assigned randomly if omitted


class IllegalAnswer(ValueError):
    """The submitted answer does not match the open decision."""


class Engine:
    def __init__(self, state: GameState, rng: random.Random) -> None:
        self.state = state
        self._rng = rng
        self._log: list[Event] = []
        self._pending: PendingDecision | None = None
        self._script: Script | None = None
        self._decision_counter = 0
        self._t = -1  # 0-based index of the turn currently executing
        self._in_endgame = False  # running end-of-game (⏰) abilities, pre-scoring
        self._scores: dict[str, ScoreBreakdown] | None = None

        self.ctx = Ctx(state, rng, self._emit, self._roll_die)

        # Cached scheduling facts (players are already rotated: first player = 0).
        self._apollo_seat: str | None = next(
            (p.seat for p in state.players if p.house is House.APOLLO), None
        )

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #

    @classmethod
    def new_game(cls, specs: list[PlayerSpec], seed: int, game_id: str = "local") -> Engine:
        if not 2 <= len(specs) <= 6:
            raise ValueError("Red Rising supports 2-6 players")
        rng = random.Random(seed)

        houses = _assign_houses(specs, rng)
        players = [
            PlayerState(seat=f"p{i}", name=spec.name, house=houses[i])
            for i, spec in enumerate(specs)
        ]
        # First player: House Apollo if present, else random. Rotate so they lead.
        first = next((i for i, p in enumerate(players) if p.house is House.APOLLO), None)
        if first is None:
            first = rng.randrange(len(players))
        players = players[first:] + players[:first]

        state = GameState(
            game_id=game_id,
            seed=seed,
            players=players,
            first_player_index=0,
            current_player_index=0,
        )
        engine = cls(state, rng)
        engine._emit(
            GameStarted(
                seed=seed,
                seats=tuple(p.seat for p in players),
                houses={p.seat: p.house for p in players},
                first_player=players[0].seat,
            )
        )
        setup_game(state, rng, engine._emit, {p.seat: p.house for p in players})
        state.assert_card_conservation()

        engine._start_first_turn()
        return engine

    # ------------------------------------------------------------------ #
    # Public surface
    # ------------------------------------------------------------------ #

    @property
    def pending(self) -> PendingDecision | None:
        return self._pending

    @property
    def events(self) -> list[Event]:
        return list(self._log)

    @property
    def finished(self) -> bool:
        return self.state.finished

    @property
    def scores(self) -> dict[str, ScoreBreakdown] | None:
        return self._scores

    def answer(self, answer: Answer) -> list[Event]:
        """Apply an answer to the open decision and run until the next one (or game end)."""
        if self._pending is None:
            raise IllegalAnswer("no decision is open")
        if answer.decision_id != self._pending.id:
            raise IllegalAnswer(
                f"stale decision id {answer.decision_id}; expected {self._pending.id}"
            )

        selected = self._resolve(self._pending, answer)
        from .events import DecisionMade

        before = len(self._log)
        self._emit(
            DecisionMade(
                seat=self._pending.seat,
                decision_id=self._pending.id,
                tokens=answer.tokens,
            )
        )
        self._pending = None
        self._run(selected)
        return self._log[before:]

    # ------------------------------------------------------------------ #
    # The pump
    # ------------------------------------------------------------------ #

    def _run(self, send_value: object) -> None:
        """Advance the current script; on completion, move to the next turn or finish."""
        while self._script is not None:
            try:
                request = self._script.send(send_value)  # type: ignore[arg-type]
            except StopIteration:
                if self._in_endgame:
                    self._finalize()
                    return
                self._end_turn()
                if not self._begin_next_turn():
                    # All turns done: resolve end-of-game abilities, then score.
                    self._in_endgame = True
                    self._script = endgame_phase(self.ctx)
                    send_value = None
                    continue
                send_value = None
                continue
            self._decision_counter += 1
            self._pending = request.with_id(self._decision_counter)
            return

    def _start_first_turn(self) -> None:
        self._begin_turn(0)
        self._run(None)

    def _resolve(self, pending: PendingDecision, answer: Answer) -> object:
        n = len(answer.tokens)
        if not (pending.min_choices <= n <= pending.max_choices):
            raise IllegalAnswer(
                f"expected between {pending.min_choices} and {pending.max_choices} choices, got {n}"
            )
        options: list[Option] = []
        for token in answer.tokens:
            opt = pending.option(token)
            if opt is None:
                raise IllegalAnswer(f"unknown option token {token!r}")
            options.append(opt)
        if pending.max_choices == 1:
            return options[0] if options else None
        return tuple(options)

    # ------------------------------------------------------------------ #
    # Turn scheduling
    # ------------------------------------------------------------------ #

    def _begin_turn(self, index: int) -> None:
        n = len(self.state.players)
        self._t = index
        self.state.current_player_index = index % n
        self.state.turn_number = index + 1  # 1-based for humans/events
        seat = self.state.players[index % n].seat
        self._emit(TurnBegan(seat=seat, turn_number=self.state.turn_number))
        self._script = play_turn(self.ctx, seat)

    def _begin_apollo_bonus_turn(self) -> None:
        assert self._apollo_seat is not None
        self.state.apollo_bonus_taken = True
        idx = next(i for i, p in enumerate(self.state.players) if p.seat == self._apollo_seat)
        self.state.current_player_index = idx
        self.state.turn_number += 1
        self._emit(TurnBegan(seat=self._apollo_seat, turn_number=self.state.turn_number))
        self._script = play_turn(self.ctx, self._apollo_seat)

    def _end_turn(self) -> None:
        # The player who just finished is always the current player (set at begin,
        # and Apollo's index for the bonus turn).
        seat = self.state.players[self.state.current_player_index].seat
        self._emit(TurnEnded(seat=seat))
        self.state.assert_card_conservation()
        check_end_trigger(self.state, self._emit, by_seat=seat)

    def _begin_next_turn(self) -> bool:
        """Start the next turn if the game continues; return False when it's over."""
        n = len(self.state.players)
        nxt = self._t + 1

        if self.state.end_triggered_on_turn is not None:
            triggered_round = self.state.end_triggered_on_turn // n
            if nxt // n > triggered_round:
                # Every player has had an equal number of turns. Apollo, if active,
                # takes one final bonus turn; then the game ends.
                if self._apollo_seat is not None and not self.state.apollo_bonus_taken:
                    self._begin_apollo_bonus_turn()
                    return True
                return False

        self._begin_turn(nxt)
        return True

    # ------------------------------------------------------------------ #
    # Finalisation
    # ------------------------------------------------------------------ #

    def _finalize(self) -> None:
        self._script = None
        self._in_endgame = False
        self.state.assert_card_conservation()  # end-game abilities moved cards around
        self.state.finished = True
        self._scores = score_game(self.state)
        self._emit(
            GameEnded(
                scores={seat: s.total for seat, s in self._scores.items()},
                winners=winners(self._scores, self.state),
            )
        )

    # ------------------------------------------------------------------ #
    # Plumbing shared with Ctx
    # ------------------------------------------------------------------ #

    def _emit(self, event: Event) -> None:
        stamped = event.model_copy(update={"seq": len(self._log)})
        self._log.append(stamped)

    def _roll_die(self, seat: str) -> DieFace:
        face = self._rng.choice(list(DieFace))
        self._emit(DieRolled(seat=seat, face=face))
        return face


def _assign_houses(specs: list[PlayerSpec], rng: random.Random) -> list[House]:
    """Honour any houses the caller pinned; fill the rest randomly, no repeats."""
    taken = {s.house for s in specs if s.house is not None}
    if len(taken) != len([s for s in specs if s.house is not None]):
        raise ValueError("duplicate houses requested")
    pool = [h for h in House if h not in taken]
    rng.shuffle(pool)
    out: list[House] = []
    for spec in specs:
        out.append(spec.house if spec.house is not None else pool.pop())
    return out
