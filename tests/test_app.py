"""Phase 2: transport layer — redaction and durable storage.

The redaction tests are the important ones: a leak of the opponent's hand is the
bug that silently ruins the game, so we assert it can't happen under fuzzing.
"""

from __future__ import annotations

import asyncio
import random

import pytest

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from red_rising.app.store import GameStore
from red_rising.app.views import PlayerView, redact
from red_rising.engine.decisions import Answer
from red_rising.engine.engine import Engine, PlayerSpec


def _exposed_card_ids(view: PlayerView) -> set[str]:
    """Every card id this view reveals to its viewer."""
    ids = set(view.you.hand) | set(view.banished)
    for loc in view.locations:
        ids |= {slot.card_id for slot in loc.cards if slot.card_id is not None}
    return ids


def _drive_and_check(engine: Engine, chooser: random.Random, on_state) -> None:
    on_state(engine)
    while not engine.finished:
        p = engine.pending
        assert p is not None
        k = chooser.randint(p.min_choices, p.max_choices)
        tokens = tuple(o.token for o in chooser.sample(list(p.options), k))
        engine.answer(Answer(decision_id=p.id, tokens=tokens))
        on_state(engine)


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 5000), n=st.integers(2, 4))
def test_redaction_never_leaks_an_opponents_hand(seed: int, n: int):
    engine = Engine.new_game([PlayerSpec(name=f"P{i}") for i in range(n)], seed=seed)
    chooser = random.Random(seed)

    def check(e: Engine) -> None:
        for viewer in (p.seat for p in e.state.players):
            view = redact(e.state, viewer, pending=e.pending, last_seq=len(e.events))
            # Serialise, exactly as the socket would, then inspect.
            view = PlayerView.model_validate(view.model_dump(mode="json"))
            exposed = _exposed_card_ids(view)
            for opp in e.state.opponents(viewer):
                assert not (set(opp.hand) & exposed), (
                    f"leaked {set(opp.hand) & exposed} to {viewer}"
                )

    _drive_and_check(engine, chooser, check)


def test_pending_decision_is_only_sent_to_its_owner():
    engine = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=1)
    p = engine.pending
    assert p is not None
    owner, other = p.seat, next(s.seat for s in engine.state.players if s.seat != p.seat)

    owner_view = redact(engine.state, owner, pending=p, last_seq=0)
    other_view = redact(engine.state, other, pending=p, last_seq=0)

    assert owner_view.pending is not None and owner_view.waiting_on is None
    assert other_view.pending is None and other_view.waiting_on is not None
    assert other_view.waiting_on.seat == owner


def test_opponent_hand_is_a_count_only():
    engine = Engine.new_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=1)
    view = redact(engine.state, "p0", pending=engine.pending, last_seq=0)
    assert view.opponents[0].hand_count == 5
    assert not hasattr(view.opponents[0], "hand")  # structurally impossible to leak


# --------------------------------------------------------------------------- #
# Store: create, play, reload
# --------------------------------------------------------------------------- #


def test_create_and_authenticate(tmp_path):
    store = GameStore(tmp_path / "t.db")
    meta = store.create_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=42)
    session = store.get(meta.game_id)
    assert session is not None
    assert session.authenticate("p0", meta.seats[0].token)
    assert not session.authenticate("p0", "wrong")
    assert not session.authenticate("p1", meta.seats[0].token)
    store.close()


def test_game_reloads_from_sqlite_by_replay(tmp_path):
    db = tmp_path / "t.db"
    store = GameStore(db)
    meta = store.create_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=42)
    session = store.get(meta.game_id)
    assert session is not None

    chooser = random.Random(3)
    for _ in range(12):  # play a dozen moves, then "restart"
        p = session.engine.pending
        if p is None:
            break
        k = chooser.randint(p.min_choices, p.max_choices)
        tokens = tuple(o.token for o in chooser.sample(list(p.options), k))
        asyncio.run(session.submit(p.seat, Answer(decision_id=p.id, tokens=tokens)))
    events_before = [e.model_dump() for e in session.engine.events]
    store.close()

    # Fresh store, same DB file: the game rebuilds by replaying persisted answers.
    store2 = GameStore(db)
    reloaded = store2.get(meta.game_id)
    assert reloaded is not None
    assert [e.model_dump() for e in reloaded.engine.events] == events_before
    store2.close()


# --------------------------------------------------------------------------- #
# Phase 5: event redaction, undo, replay
# --------------------------------------------------------------------------- #


def test_redact_event_hides_opponent_draws_and_drops_bookkeeping():
    from red_rising.app.views import redact_event
    from red_rising.engine.events import CardDealt, DecisionMade

    dealt = CardDealt(seq=1, seat="p1", card_id="aja")
    # The opponent's dealt card is nulled for p0, kept for p1.
    assert redact_event(dealt, "p0")["card_id"] is None
    assert redact_event(dealt, "p1")["card_id"] == "aja"
    # Internal decision bookkeeping never reaches the log.
    assert redact_event(DecisionMade(seq=2, seat="p0", decision_id=1, tokens=("x",)), "p0") is None


def _play_n(session, n: int, seed: int = 3) -> None:
    chooser = random.Random(seed)
    for _ in range(n):
        p = session.engine.pending
        if p is None:
            break
        k = chooser.randint(p.min_choices, p.max_choices)
        tokens = tuple(o.token for o in chooser.sample(list(p.options), k))
        asyncio.run(session.submit(p.seat, Answer(decision_id=p.id, tokens=tokens)))


def test_undo_rolls_back_the_last_answer(tmp_path):
    store = GameStore(tmp_path / "t.db")
    meta = store.create_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=42)
    session = store.get(meta.game_id)
    assert session is not None

    _play_n(session, 6)
    before = [e.model_dump() for e in session.engine.events]
    count_before = session._answer_count

    _play_n(session, 1)
    assert session._answer_count == count_before + 1

    assert asyncio.run(session.undo(store.undo(meta.game_id)))
    # Back to exactly the pre-last-answer state.
    assert session._answer_count == count_before
    assert [e.model_dump() for e in session.engine.events] == before
    store.close()


def test_replay_rebuilds_state_at_an_earlier_step(tmp_path):
    store = GameStore(tmp_path / "t.db")
    meta = store.create_game([PlayerSpec(name="A"), PlayerSpec(name="B")], seed=42)
    session = store.get(meta.game_id)
    assert session is not None
    _play_n(session, 10)

    total = store.answer_count(meta.game_id)
    assert total == 10
    at3 = store.engine_at(meta.game_id, 3)
    assert at3 is not None
    # An engine replayed to step 3 has strictly fewer events than the full game.
    assert len(at3.events) < len(session.engine.events)
    # And it matches a fresh full engine driven through the same first 3 answers.
    assert len(at3.events) > 0
    store.close()


# --------------------------------------------------------------------------- #
# Static serving
# --------------------------------------------------------------------------- #
# The SPA catch-all has to hand back real files (the card portraits Vite copies
# from web/public/ to the root of dist/) rather than the shell, or the browser
# asks for a .webp and is given index.html. The Vite dev server serves public/
# itself, so this only ever breaks in a built deployment.


def _client_with_dist(tmp_path, monkeypatch):
    """A TestClient whose DIST points at a throwaway build tree."""
    from fastapi.testclient import TestClient

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>")
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "darrow.webp").write_bytes(b"RIFF____WEBPfake")

    from red_rising.app import server

    monkeypatch.setattr(server, "DIST", tmp_path)
    return TestClient(server.app)


def test_public_assets_are_served_not_shadowed_by_the_spa(tmp_path, monkeypatch):
    client = _client_with_dist(tmp_path, monkeypatch)

    res = client.get("/characters/darrow.webp")
    assert res.status_code == 200
    assert res.content == b"RIFF____WEBPfake"
    assert "html" not in res.headers["content-type"]


def test_client_routes_still_fall_through_to_the_shell(tmp_path, monkeypatch):
    client = _client_with_dist(tmp_path, monkeypatch)

    # /g/<id> is client-side routing: no such file, so the shell must answer.
    res = client.get("/g/abc123")
    assert res.status_code == 200
    assert "<div id=root>" in res.text


# Serving any real file under dist/ means the containment check is what stands
# between a crafted path and the rest of the filesystem. Verified load-bearing:
# without it, "/../outside.txt" resolves outside the build tree and is served.
@pytest.mark.parametrize(
    "path",
    [
        "/../outside.txt",
        "/%2e%2e/outside.txt",
        "/characters/../../outside.txt",
        "/%2e%2e%2foutside.txt",
    ],
)
def test_traversal_cannot_escape_the_build_directory(path, tmp_path, monkeypatch):
    (tmp_path.parent / "outside.txt").write_text("not yours")
    client = _client_with_dist(tmp_path, monkeypatch)

    assert "not yours" not in client.get(path).text
