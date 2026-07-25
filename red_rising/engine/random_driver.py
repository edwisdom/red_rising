"""Drive a game to completion by answering every decision at random.

This is the workhorse for testing: it exercises the whole turn engine without a UI
and, under Hypothesis, fuzzes thousands of playthroughs. It also backs the `cli`
entry point for eyeballing a game.
"""

from __future__ import annotations

import random

from .decisions import Answer
from .engine import Engine, PlayerSpec
from .scoring import ScoreBreakdown


def play_random_game(
    seed: int,
    n_players: int = 2,
    *,
    max_turns: int = 2000,
) -> Engine:
    """Play a full game; every decision is answered by a uniformly random option.

    `max_turns` is a safety valve against a rules bug that fails to progress; a real
    2-player game ends in well under a hundred decisions.
    """
    chooser = random.Random(seed ^ 0x5DEECE66D)
    specs = [PlayerSpec(name=f"Player {i + 1}") for i in range(n_players)]
    engine = Engine.new_game(specs, seed=seed)

    steps = 0
    while not engine.finished:
        pending = engine.pending
        assert pending is not None, "not finished but no decision open"
        k = chooser.randint(pending.min_choices, pending.max_choices)
        tokens = tuple(o.token for o in chooser.sample(list(pending.options), k))
        engine.answer(Answer(decision_id=pending.id, tokens=tokens))
        steps += 1
        if steps > max_turns:
            raise RuntimeError(f"game {seed} did not terminate in {max_turns} decisions")
    return engine


def format_result(engine: Engine) -> str:
    scores: dict[str, ScoreBreakdown] = engine.scores or {}
    header = f"Game {engine.state.game_id} (seed {engine.state.seed}) — {len(engine.events)} events"
    lines = [header]
    ranked = sorted(engine.state.players, key=lambda p: -(scores[p.seat].total))
    for p in ranked:
        s = scores[p.seat]
        mark = "  <- winner" if p.seat in engine.events[-1].winners else ""  # type: ignore[attr-defined]
        lines.append(
            f"  {p.name:10s} {p.house.value:8s} {s.total:4d} pts "
            f"(core {s.core_values}, fleet {s.fleet}, He {s.helium}, "
            f"sov {s.sovereignty}, inf {s.influence}, excess {s.excess_penalty}){mark}"
        )
    return "\n".join(lines)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Play a random Red Rising game")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--players", type=int, default=2)
    args = ap.parse_args()
    engine = play_random_game(args.seed, args.players)
    print(format_result(engine))


if __name__ == "__main__":
    main()
