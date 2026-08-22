# Red Rising — digital board game

A two-player web implementation of Stonemaier's *Red Rising*, for playing with a
partner over a private link. Live, both-online play; data-driven cards; a pure,
headless rules engine.

## Status

| Phase | What | State |
|---|---|---|
| 0 | Card data pipeline (parquet → validated `cards.json`) | ✅ done |
| 1 | Pure engine: turns, bonuses, house tiles, game-end, base scoring | ✅ done |
| 2 | Web shell: FastAPI + WebSocket + React, redaction, deploy config | ✅ done |
| 3 | Card abilities — all 107 deploy scripts + 5 block cards | ✅ done |
| 4 | Full end-game scoring — 127 bonus clauses, wildcards, ⏰ abilities | ✅ done |
| 5 | Polish — event log, animations, reconnect, undo, replay | ✅ done |

**The game is complete.** Every card's deploy/block ability works, the final score
is fully computed (127 bonus clauses + Gray/Orange wildcard optimisation + the 11
interactive end-of-game abilities), and the UI has a live event-log sidebar,
card animations, a connection indicator with auto-reconnect, undo-last-action, and
a full-game replay scrubber that reconstructs the board at any step.

## Architecture

For the full engineering picture — the mental model, load-bearing decisions and *why*,
the traps, and where everything lives — see **[HANDOFF.md](HANDOFF.md)**. Short version:

```
red_rising/
  enums.py         # Color/Location/House/DieFace + all scoring constants
  carddefs.py      # immutable card faces; load_cards() reads data/cards.json
  data/            # build_cards.py (parquet -> cards.json), parse.py, cards.json
  engine/          # PURE core — no FastAPI, no I/O, no async
    state.py       #   zones + card-conservation invariant
    decisions.py   #   Decision/Option/Answer (the pending decision IS legal_actions)
    events.py      #   append-only event log (discriminated union)
    context.py     #   Ctx: the verbs scripts are written in
    rules.py       #   turn flow as generators; bonuses, die, house tiles, game-end
    engine.py      #   the pump: drives scripts, answers decisions, schedules turns
    scoring.py     #   base scoring (card bonuses plug in at Phase 4)
    random_driver.py  # play a full game answering randomly (tests + CLI)
  app/             # thin transport — FastAPI, no game rules
    views.py       #   redact(state, viewer) -> PlayerView  (never leaks a hand)
    store.py       #   in-memory sessions + SQLite answer-log durability
    server.py      #   REST + WebSocket + serves the built SPA
web/               # React 19 + Vite + TypeScript + Tailwind v4
  src/theme.ts     #   the printed game's caste palette + location colours
  src/components/  #   Icons (the game's own iconography), CardView, CardZoom…
  public/characters/  # 112 character portraits, one per card
```

**Why a pure engine.** Everything is `(state, answer) -> events`, deterministic
from a seed. That single decision buys replay, fuzzing, trivial persistence
(store answers, replay them — no serialised engine), and a future bot for free.

**The turn is a generator.** `play_turn` yields a `Decision` whenever a player must
choose and runs mechanical steps in between. Card abilities (Phase 3) are nested
scripts driven by the same pump — so none of the turn engine is throwaway.

## Develop

Backend and a watching frontend, in two terminals:

```bash
uv run uvicorn red_rising.app.server:app --reload    # :8000
```

```bash
npm --prefix web install
npm --prefix web run dev                             # :5173, proxies /api + /ws
```

Open http://localhost:5173, create a game, and open the partner link in a second
browser (or a private window — credentials are per-tab, so two normal tabs work too).

Watch a full game play itself:

```bash
uv run python -m red_rising.engine.random_driver --seed 1
```

Regenerate card data after editing the parquet:

```bash
uv run python -m red_rising.data.build_cards
```

## Test

```bash
uv run pytest        # engine invariants, replay determinism, redaction, scoring
uv run ruff check .
```

The load-bearing tests: **card conservation** (all 112 cards in exactly one zone,
every turn), **replay determinism** (seed + answers → identical event log), and
**redaction never leaks a hand** (fuzzed).

## Deploy (single private container)

```bash
docker build -t red-rising .
docker run -p 8000:8000 -v rr_data:/data red-rising
```

Or Fly.io (see `fly.toml`):

```bash
fly launch --no-deploy
fly volumes create rr_data --size 1
fly deploy
```

Auth is the unguessable game link plus a per-seat token — no accounts. Keep the
app URL between you and your partner. One instance only: live games are held in
memory (and survive restarts by replaying the SQLite answer log).

## Provenance

Built from a personal copy of the game for private two-player use. Card text lives
in `red_rising_characters.parquet`; the rules digest is `red-rising-rulebook.md`.
The character portraits in `web/public/characters/` and the card iconography in
`web/src/components/Icons.tsx` are the game's own artwork, taken from the public
rules reference at <https://red-rising.rulepop.com/>.
*Red Rising* is © Pierce Brown; tabletop rights Stonemaier Games. Artwork remains
theirs. Don't redistribute the card data or artwork, or run this as a public service.
