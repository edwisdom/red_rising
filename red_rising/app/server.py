"""FastAPI transport: REST to create/join games, WebSocket for live play.

Run in development (with the Vite dev server proxying to it):

    uv run uvicorn red_rising.app.server:app --reload

In production the same process also serves the built SPA from `web/dist`.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from red_rising.carddefs import CARDS_JSON
from red_rising.engine.decisions import Answer
from red_rising.engine.engine import PlayerSpec

from .schemas import CreateGameRequest, CreateGameResponse, SeatOut
from .store import GameStore
from .views import redact_event

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST = Path(os.environ.get("RR_WEB_DIST", REPO_ROOT / "web" / "dist"))
DB_PATH = os.environ.get("RR_DB", str(REPO_ROOT / "red_rising.db"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = GameStore(DB_PATH)
    try:
        yield
    finally:
        app.state.store.close()


app = FastAPI(title="Red Rising", lifespan=lifespan)


def store() -> GameStore:
    return app.state.store


# --------------------------------------------------------------------------- #
# REST
# --------------------------------------------------------------------------- #


@app.post("/api/games", response_model=CreateGameResponse)
def create_game(req: CreateGameRequest) -> CreateGameResponse:
    specs = [PlayerSpec(name=p.name, house=p.house) for p in req.players]
    try:
        meta = store().create_game(specs, req.seed)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return CreateGameResponse(
        game_id=meta.game_id,
        seats=[SeatOut(seat=s.seat, name=s.name, token=s.token) for s in meta.seats],
    )


@app.get("/api/games/{game_id}/view")
def get_view(game_id: str, seat: str, token: str):
    session = store().get(game_id)
    if session is None:
        raise HTTPException(404, "no such game")
    if not session.authenticate(seat, token):
        raise HTTPException(403, "bad seat or token")
    return session.view_for(seat)


@app.get("/api/cards")
def get_cards():
    """Card definitions, so the client renders identical faces to the server."""
    return JSONResponse(json.loads(CARDS_JSON.read_text()))


@app.get("/api/games/{game_id}/replay")
def replay(game_id: str, seat: str, token: str, step: int):
    """Rebuild the game as it stood after `step` answers, for the replay scrubber."""
    session = store().get(game_id)
    if session is None or not session.authenticate(seat, token):
        raise HTTPException(403, "bad seat or token")
    total = store().answer_count(game_id)
    engine = store().engine_at(game_id, max(0, min(step, total)))
    if engine is None:
        raise HTTPException(404, "no such game")
    from .views import redact

    view = redact(
        engine.state, seat, pending=None, last_seq=len(engine.events), scores=engine.scores
    )
    events = [redact_event(e, seat) for e in engine.events]
    return JSONResponse(
        {
            "view": view.model_dump(mode="json"),
            "events": [e for e in events if e is not None],
            "step": min(step, total),
            "total": total,
        }
    )


# --------------------------------------------------------------------------- #
# WebSocket
# --------------------------------------------------------------------------- #


@app.websocket("/ws/{game_id}")
async def play(ws: WebSocket, game_id: str, seat: str, token: str) -> None:
    session = store().get(game_id)
    if session is None or not session.authenticate(seat, token):
        await ws.close(code=4403)  # policy violation: bad game/seat/token
        return
    await ws.accept()

    import asyncio

    queue = session.subscribe()
    sent = 0  # how many events this socket has already received

    async def push() -> None:
        nonlocal sent
        events = session.engine.events
        reset = len(events) < sent  # an undo shrank the log; resend from scratch
        if reset:
            sent = 0
        new = [redact_event(e, seat) for e in events[sent:]]
        sent = len(events)
        await ws.send_json(
            {
                "type": "view",
                "view": session.view_for(seat).model_dump(mode="json"),
                "events": [e for e in new if e is not None],
                "reset": reset,
            }
        )

    try:
        await push()

        async def pusher() -> None:
            while True:
                await queue.get()
                await push()

        async def reader() -> None:
            while True:
                msg = await ws.receive_json()
                await _handle_message(ws, session, seat, msg, push)

        push_task = asyncio.create_task(pusher())
        read_task = asyncio.create_task(reader())
        _, still = await asyncio.wait({push_task, read_task}, return_when=asyncio.FIRST_COMPLETED)
        for t in still:
            t.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        session.unsubscribe(queue)


async def _handle_message(ws: WebSocket, session, seat: str, msg: dict, push) -> None:
    kind = msg.get("type")
    if kind == "answer":
        try:
            answer = Answer(decision_id=int(msg["decision_id"]), tokens=tuple(msg["tokens"]))
            await session.submit(seat, answer)
        except (PermissionError, ValueError, KeyError) as e:
            # Stale/illegal (e.g. both clients racing): tell this client and resync.
            await ws.send_json({"type": "error", "message": str(e)})
            await push()
    elif kind == "undo":
        await session.undo(store().undo(session.engine.state.game_id))


# --------------------------------------------------------------------------- #
# Static SPA (mounted last so it never shadows /api or /ws)
# --------------------------------------------------------------------------- #

if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str) -> Response:
    """Serve a built file if one exists at that path, else the SPA shell.

    Vite copies everything in `web/public/` (the 112 card portraits) to the root
    of `dist/`, not into `dist/assets/`, so mounting /assets alone left those
    paths falling through to the shell — the browser asked for a .webp and got
    index.html back. Dev never showed it because Vite serves public/ itself.

    `resolve()` plus the containment check is what keeps a crafted "../" path
    from reading outside the build directory.
    """
    if full_path:
        candidate = (DIST / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(DIST.resolve()):
            return FileResponse(candidate)
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse(
        {"detail": "frontend not built; run `npm --prefix web run build` or the Vite dev server"},
        status_code=503,
    )
