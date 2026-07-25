"""Game storage: live sessions in memory, durable answer log in SQLite.

Durability leans entirely on the engine's determinism (proved by
`test_replay_from_recorded_answers_is_deterministic`): we persist only the game's
seed, its player specs, and the ordered list of answers. To reload a game we
`new_game(...)` and replay the answers — no serialised engine, no snapshot format
to maintain. That is the whole payoff of the pure-core design.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sqlite3
import time
from pathlib import Path

from pydantic import BaseModel

from red_rising.engine.decisions import Answer
from red_rising.engine.engine import Engine, PlayerSpec
from red_rising.enums import House

from .views import PlayerView, redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id    TEXT PRIMARY KEY,
    seed       INTEGER NOT NULL,
    created_at REAL NOT NULL,
    specs      TEXT NOT NULL,   -- JSON: [{name, house|null}, ...] in seat order
    tokens     TEXT NOT NULL    -- JSON: {seat: token}
);
CREATE TABLE IF NOT EXISTS answers (
    game_id     TEXT NOT NULL,
    idx         INTEGER NOT NULL,
    decision_id INTEGER NOT NULL,
    tokens      TEXT NOT NULL,   -- JSON: [token, ...]
    PRIMARY KEY (game_id, idx)
);
"""


class SeatInfo(BaseModel):
    seat: str
    name: str
    token: str


class GameMeta(BaseModel):
    game_id: str
    seats: list[SeatInfo]


class GameSession:
    """One live game: the engine, a lock serialising answers, and WS subscribers."""

    def __init__(
        self,
        engine: Engine,
        tokens: dict[str, str],
        names: dict[str, str],
        on_answer,
    ) -> None:
        self.engine = engine
        self._tokens = tokens
        self._names = names
        self._on_answer = on_answer  # persist callback(game_id, idx, answer)
        self._answer_count = 0
        self.lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[int]] = set()
        self.version = 0

    # -- auth --

    def authenticate(self, seat: str, token: str) -> bool:
        expected = self._tokens.get(seat)
        return expected is not None and secrets.compare_digest(expected, token)

    def seat_name(self, seat: str) -> str | None:
        return self._names.get(seat)

    # -- views --

    def view_for(self, seat: str) -> PlayerView:
        return redact(
            self.engine.state,
            seat,
            pending=self.engine.pending,
            last_seq=len(self.engine.events),
            scores=self.engine.scores,
        )

    # -- answers --

    async def submit(self, seat: str, answer: Answer) -> None:
        """Apply an answer from `seat`, persist it, and wake subscribers."""
        async with self.lock:
            pending = self.engine.pending
            if pending is None:
                raise PermissionError("no decision is open")
            if pending.seat != seat:
                raise PermissionError("not your decision")
            if pending.id != answer.decision_id:
                raise PermissionError("stale decision")

            self.engine.answer(answer)
            idx = self._answer_count
            self._answer_count += 1
            self._on_answer(self.engine.state.game_id, idx, answer)
            self.version += 1
            self._notify()

    async def undo(self, undo_last) -> bool:
        """Roll the game back one answer. `undo_last` rebuilds and returns a fresh
        engine (or None if there is nothing to undo)."""
        async with self.lock:
            rebuilt = undo_last()
            if rebuilt is None:
                return False
            self.engine, self._answer_count = rebuilt
            self.version += 1
            self._notify()
            return True

    def _notify(self) -> None:
        for q in self._subscribers:
            q.put_nowait(self.version)

    def subscribe(self) -> asyncio.Queue[int]:
        q: asyncio.Queue[int] = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[int]) -> None:
        self._subscribers.discard(q)


class GameStore:
    def __init__(self, db_path: Path | str = "red_rising.db") -> None:
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.executescript(_SCHEMA)
        self._db.commit()
        self._sessions: dict[str, GameSession] = {}

    # -- creation --

    def create_game(self, specs: list[PlayerSpec], seed: int | None = None) -> GameMeta:
        game_id = secrets.token_urlsafe(9)
        if seed is None:
            seed = secrets.randbelow(2**31)
        engine = Engine.new_game(specs, seed=seed, game_id=game_id)

        # Seat i is p{i}, keyed to the spec order (engine rotates play order, not ids).
        tokens = {f"p{i}": secrets.token_urlsafe(16) for i in range(len(specs))}
        names = {f"p{i}": spec.name for i, spec in enumerate(specs)}

        specs_json = json.dumps(
            [{"name": s.name, "house": s.house.value if s.house else None} for s in specs]
        )
        self._db.execute(
            "INSERT INTO games (game_id, seed, created_at, specs, tokens) VALUES (?, ?, ?, ?, ?)",
            (game_id, seed, time.time(), specs_json, json.dumps(tokens)),
        )
        self._db.commit()

        session = GameSession(engine, tokens, names, self._persist_answer)
        self._sessions[game_id] = session
        return GameMeta(
            game_id=game_id,
            seats=[
                SeatInfo(seat=f"p{i}", name=s.name, token=tokens[f"p{i}"])
                for i, s in enumerate(specs)
            ],
        )

    # -- retrieval (loads + replays from SQLite on a cache miss) --

    def get(self, game_id: str) -> GameSession | None:
        if game_id in self._sessions:
            return self._sessions[game_id]
        meta = self._meta(game_id)
        if meta is None:
            return None
        seed, specs, tokens, names = meta
        engine, n = self._build_engine(game_id, seed, specs)
        session = GameSession(engine, tokens, names, self._persist_answer)
        session._answer_count = n
        self._sessions[game_id] = session
        return session

    def undo(self, game_id: str):
        """Return a callable that deletes the last answer and rebuilds the engine.

        Passed to `GameSession.undo` so the DB mutation and swap happen under the
        session lock.
        """
        meta = self._meta(game_id)

        def do_undo():
            if meta is None:
                return None
            seed, specs, _, _ = meta
            last = self._db.execute(
                "SELECT MAX(idx) FROM answers WHERE game_id = ?", (game_id,)
            ).fetchone()[0]
            if last is None:
                return None
            self._db.execute("DELETE FROM answers WHERE game_id = ? AND idx = ?", (game_id, last))
            self._db.commit()
            return self._build_engine(game_id, seed, specs)

        return do_undo

    def engine_at(self, game_id: str, step: int) -> Engine | None:
        """A throwaway engine replayed through exactly `step` answers (for replay)."""
        meta = self._meta(game_id)
        if meta is None:
            return None
        seed, specs, _, _ = meta
        engine, _ = self._build_engine(game_id, seed, specs, limit=step)
        return engine

    def answer_count(self, game_id: str) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) FROM answers WHERE game_id = ?", (game_id,)
        ).fetchone()
        return row[0] if row else 0

    # -- rebuild helpers --

    def _meta(self, game_id: str):
        row = self._db.execute(
            "SELECT seed, specs, tokens FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()
        if row is None:
            return None
        seed, specs_json, tokens_json = row
        specs = [
            PlayerSpec(name=s["name"], house=House(s["house"]) if s["house"] else None)
            for s in json.loads(specs_json)
        ]
        tokens = json.loads(tokens_json)
        names = {f"p{i}": s.name for i, s in enumerate(specs)}
        return seed, specs, tokens, names

    def _build_engine(self, game_id: str, seed: int, specs, *, limit: int | None = None):
        """Fresh engine replayed through the persisted answers (up to `limit`)."""
        engine = Engine.new_game(specs, seed=seed, game_id=game_id)
        rows = self._db.execute(
            "SELECT decision_id, tokens FROM answers WHERE game_id = ? ORDER BY idx", (game_id,)
        ).fetchall()
        if limit is not None:
            rows = rows[:limit]
        for decision_id, tok_json in rows:
            if engine.finished:
                break
            engine.answer(Answer(decision_id=decision_id, tokens=tuple(json.loads(tok_json))))
        return engine, len(rows)

    def _persist_answer(self, game_id: str, idx: int, answer: Answer) -> None:
        self._db.execute(
            "INSERT INTO answers (game_id, idx, decision_id, tokens) VALUES (?, ?, ?, ?)",
            (game_id, idx, answer.decision_id, json.dumps(list(answer.tokens))),
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()
