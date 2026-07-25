# Red Rising — Engineering Handoff

A digital, two-player implementation of Stonemaier's *Red Rising* board game, playable
in a browser and deployable behind a private link. This document is for the next
engineer or coding agent. It explains **what exists, how it fits together, and — most
importantly — why it is built this way**, so you can change it without breaking the
parts that are load-bearing.

Read [README.md](README.md) first for the one-paragraph pitch and run/deploy commands.
This document goes deeper.

**Status: complete.** All five planned phases are done. Every card's deploy and block
ability works, the end-game score is fully computed, and the UI has an event log,
animations, reconnect, undo, and replay. 202 tests pass.

---

## 1. The one idea to understand first

Everything hinges on a single architectural decision:

> **The game rules are a *pure* engine. The turn flow and every card ability are
> Python *generators* that `yield` a decision whenever a player must choose.**

"Pure" means `red_rising/engine/` imports no web framework, does no I/O, and is not
`async`. It is deterministic given a seed. Concretely, a game is:

```
Engine.new_game(specs, seed)  →  a sequence of (pending decision) → (answer) steps  →  final scores
```

Because the engine is pure and deterministic, four things fall out **for free**, and
you should preserve all of them:

1. **Persistence is trivial.** We store only the seed, the player specs, and the
   ordered list of answers. To rebuild any game we call `new_game(...)` and replay the
   answers. There is no serialized engine, no snapshot format. (`app/store.py`)
2. **Undo is trivial.** Drop the last answer, replay the rest. (that's literally the
   implementation)
3. **Replay is trivial.** Replay the first *N* answers to reconstruct the board at
   step *N*. (the replay scrubber)
4. **A bot would be cheap.** The set of legal moves is always exactly the options on
   the current pending decision — no separate move generator to write.

If you find yourself wanting to serialize the engine, snapshot mid-turn state, or add
`async`/I/O inside `engine/`, stop — you are about to break the thing that makes the
rest simple.

### The turn *is* a script

A subtle but important consequence: the **turn flow itself** (`engine/rules.py:play_turn`)
is written with the same generator machinery as card abilities. There is no separate
"turn engine" and "ability engine". When a card's deploy ability needs the player to
choose, it `yield`s a decision; when the turn needs the player to choose Lead vs Scout,
it `yield`s a decision. The engine's pump (`engine/engine.py:_run`) drives whichever
generator is active. Card abilities plug in at the deploy point in `_lead` via
`yield from trigger_deploy(...)`.

This is why we never had to throw away a "Phase 1" turn engine when we added abilities.

---

## 2. Why per-card Python scripts (and not a rules DSL)

The 112 cards' ability text was analyzed up front. After normalizing away names,
colors, and numbers, **98 of the 107 deploy abilities are structurally distinct.**
There is almost no reuse. A generic data-driven rules language ("DSL") would have had
to grow into a full programming language to express them — the classic trap.

So each card ability is a small Python function, written to read against the printed
card text (the text is its docstring). A shared library of ~25 primitives (`Ctx`) and
helper generators (`choose_card`, `choose_other_location`, …) keeps each card short.
The same philosophy is used for **scoring** (one function per card's bonus clauses).

This is the single most important design decision to respect. When you add or fix a
card, you write/edit its function; you do not extend a config schema.

---

## 3. Repository map

```
red_rising/
  enums.py            # Color (14 castes), Location (4), House (6), DieFace, scoring constants.
                      #   Dependency-free. Everything imports from here. NOTE: Color is a StrEnum.
  carddefs.py         # Immutable printed card faces (CardDef/Ability/BonusClause/Ref).
                      #   load_cards() (cached) reads data/cards.json — never the parquet.
  data/
    parse.py          # Markdown → structured: AnchorResolver, clause splitting.
    build_cards.py    # parquet → validated cards.json. THE ONLY place pandas/pyarrow are used.
    cards.json        # Generated, checked in. The engine + frontend both read this.

  engine/             # THE PURE CORE. No FastAPI, no async, no I/O. Ever.
    state.py          #   GameState / PlayerState / LocationStack. assert_card_conservation().
    decisions.py      #   DecisionRequest / Option / PendingDecision / Answer.
                      #     There is NO separate legal_actions(): the pending decision's
                      #     enumerated options ARE the legal moves.
    events.py         #   Append-only event log. Discriminated union on `type`. `seq` stamped on emit.
    context.py        #   Ctx: the ~25 verbs scripts are written in (mechanical ops + choose_* builders).
    rules.py          #   Turn flow as generators (play_turn/_lead/_scout), setup, game-end trigger.
    bonuses.py        #   Location bonuses, the die, house tiles, gain_sovereign. Shared by rules + cards.
    abilities.py      #   Deploy-ability machine: @deploy registry, Deploy frame, trigger_deploy,
                      #     shared choose_* helpers, and the block/steal primitives.
    cards/            # 107 deploy scripts total, split by complexity:
      tier0.py        #   38 straight-line + simple-conditional deploy scripts.
      tier1.py        #   21 conditional (banish/gain then test) deploy scripts.
      tier2.py        #   35 player-choice, self-only scripts (grab/magnet/reveal-2-under families…).
      tier3.py        #   13 opponent-interactive scripts (steal, forced banish, Loan Shark nested turn).
    endgame.py        #   11 interactive end-of-game (⏰) ability scripts + endgame_phase(ctx).
    scoring/
      base.py         #   Token scoring + orchestration (score_game/winners/score_influence).
      context.py      #   ScoreCtx: wildcard-aware queries (has/count/for_each/…).
      scorers.py      #   @score registry, 102 per-card bonus functions.
      wildcards.py    #   Gray/Orange assignment optimizer; best_bonus_total() is the entry point.
    engine.py         #   The Engine: new_game/answer, the pump (_run), turn scheduling, finalize.
    random_driver.py  #   play_random_game(seed, n): answers every decision at random. Tests + CLI.

  app/                # THIN transport. May use FastAPI/async/I/O. Holds NO game rules.
    views.py          #   redact(state, viewer) -> PlayerView; redact_event(event, viewer).
    store.py          #   GameStore (SQLite) + GameSession (engine + lock + WS subscribers). Undo/replay.
    server.py         #   REST + WebSocket + serves the built SPA.
    schemas.py        #   REST request/response bodies.

web/                  # React 19 + Vite + TypeScript + Tailwind v4 + Zustand + framer-motion.
  src/
    types.ts          #   Hand-written wire types (kept in sync with app/views.py).
    cards.ts          #   Loads /api/cards; caste display colors.
    store.ts          #   Zustand store: view, events, replay state, connection status.
    ws.ts             #   WebSocket wrapper: auto-reconnect, event deltas, undo().
    eventText.ts      #   describeEvent(): maps an event to a human-readable log line.
    components/       #   Game, Lobby, CardView, LocationPile, PlayerPanel, DecisionBar,
                      #     Scoreboard, EventLog, ReplayBar.

tests/                # 202 tests. See §8.
Dockerfile, fly.toml  # Single-container deploy (built SPA served by FastAPI; SQLite on a volume).
red-rising-rulebook.md          # The full rules, cleanly extracted. Implement from this.
red_rising_characters.parquet   # Source card data. Personal-use only; do not redistribute.
```

---

## 4. How a turn flows (the control loop)

`engine/engine.py` is the heart. `Engine.answer(answer)`:

1. Validates the answer against the single open `pending` decision.
2. Records a `DecisionMade` event (this is what replay feeds back).
3. Resumes the live generator with the chosen `Option(s)` via `_run`.
4. `_run` pumps the generator until it `yield`s the next decision (park it, return) or
   the generator finishes (advance to the next turn, or — when all turns are done — run
   the **end-game ability phase**, then score).

The generator is held **in memory only** — it is never serialized. On a server restart
or reconnect, the game rebuilds by replaying answers (see §6), which re-runs the
generators deterministically.

**Turn scheduling** (in `engine.py`) implements: fixed clockwise order from the first
player; game-end triggers when the thresholds are met; then everyone finishes to an
equal number of turns; then **House Apollo takes one extra final turn** if present.
This is fiddly; there are targeted tests (`test_engine.py::test_apollo_leads_and_takes_the_final_bonus_turn`,
`test_players_take_equal_turns_without_apollo`). Touch it carefully.

---

## 5. The ability system in detail

### Deploy abilities (`engine/abilities.py` + `engine/cards/`)

- A card ability is a function registered with `@deploy("card-id")`. It receives a
  `Deploy` frame (`d`): the source card, the location it was deployed to, and
  `d.under_at_deploy` — **the card that was directly beneath it, captured at deploy
  time** (so "if deployed on top of a Gold" stays correct even after the ability moves
  cards around).
- A script may be a **plain function** (runs immediately, no player input) or a
  **generator function** (`yield`s decisions). `trigger_deploy` handles both via
  `inspect.isgenerator` — plain functions run eagerly, generators are driven with
  `yield from`. This is why simple cards read as simple straight-line code.
- Scripts talk to the game only through `d.ctx` (the `Ctx` primitives) and the shared
  `choose_*` helpers. They do not touch `GameState` fields directly (much).

### Blocks live in the primitives, not the cards

The 5 block cards (Judge/Howlers/Pax reveal to block a steal or banish; Justice/Martyr
reveal-and-banish to keep the Sovereign) are **not** implemented as card scripts. Instead,
three primitives — `steal_card`, `force_banish_own_card`, `banish_opponent_card` (in
`abilities.py`) — open the block window automatically by checking the target's hand.
Sovereign theft is handled in `bonuses.gain_sovereign`, which **every** sovereign gain
routes through (Luna bonus, the die, Boneriders, Jackal). So no offensive card script
knows blocks exist. If you add a card that steals or force-banishes, use these
primitives and you get blocking for free.

### Opponent decisions are free

A `DecisionRequest` carries the `seat` that must answer. The engine parks it, and the
redaction/WebSocket layer surfaces it to exactly that player (others see "waiting
on…"). So a card that makes an opponent choose just addresses a prompt to their seat —
no special machinery. `choose_opponent` auto-resolves when there is a single opponent.

### Re-entrancy: Loan Shark

Loan Shark lets an opponent take an entire turn *nested inside yours*. Because the turn
is itself a generator, this is just `yield from play_turn(ctx, opp)` inside the Loan
Shark script (with a function-local import to avoid a module cycle). The pump drives
the nested turn transparently. This was the hardest case in the design and it works;
if you ever refactor the pump, keep this test passing.

---

## 6. Persistence, undo, and replay (`app/store.py`)

- **Schema:** `games(game_id, seed, specs, tokens)` and `answers(game_id, idx,
  decision_id, tokens)`. That's it. No board state is ever stored.
- **Load / reconnect:** `_build_engine(seed, specs)` = `new_game` + replay all answers.
- **Undo:** `GameStore.undo(game_id)` returns a callable that deletes the last answer
  row and rebuilds; `GameSession.undo` runs it under the session lock and swaps in the
  fresh engine. The event log shrinks, and the WebSocket sends a `reset` flag so
  clients clear and reload their log.
- **Replay:** `engine_at(game_id, step)` rebuilds replaying only the first `step`
  answers; `GET /api/games/{id}/replay?step=N` returns the redacted view + log at that
  point. The frontend scrubber calls it.

This all works *only because* the engine is deterministic. Recorded RNG note: all
randomness goes through one seeded `random.Random`; the same seed + same answers →
byte-identical event log (`test_engine.py::test_replay_from_recorded_answers_is_deterministic`).

---

## 7. The app and frontend layers

### Redaction is the security boundary (`app/views.py`)

`redact(state, viewer)` produces the `PlayerView` a client sees. It is **structurally
impossible** to leak a hand: opponents are represented by an `OpponentView` that has
`hand_count`, not `hand`. The deck is a count. Face-down location cards are hidden.
A pending decision is sent only to its owner. `redact_event` similarly nulls opponent
draw card-ids and drops internal bookkeeping events. A fuzz test asserts no opponent
hand card ever appears in any viewer's serialized view
(`test_app.py::test_redaction_never_leaks_an_opponents_hand`). If you add state to the
view, run that test.

### Auth: link + token, per tab

No accounts. A game has an unguessable id and a per-seat token; the join link carries
the token. Credentials live in **`sessionStorage`, not `localStorage`** — deliberately,
so two seats opened in one browser (or the creator's two links) don't clobber each
other, and because the link itself is the durable credential.

### Frontend

Server state is authoritative; the client is a thin renderer fed by one WebSocket into
a Zustand store. Card faces are rendered from `cards.json` (`CardView`) — no art assets
(there's an `art_url` slot on `CardDef` for later). Interaction is **click-to-answer**
(highlight valid cards/locations, click to choose) rather than drag-and-drop, because
the engine is decision-driven and click maps to it cleanly. The wire types in
`types.ts` are hand-maintained against `app/views.py`; if you change a view, update
both (or wire up openapi-typescript, which was deferred).

---

## 8. How to trust a change (tests & invariants)

Run `uv run pytest` (202 tests, ~11s). The load-bearing ones:

- **Card conservation** — every one of the 112 cards is in exactly one zone at all
  times. Checked after every turn and at finalize (`state.assert_card_conservation()`),
  and fuzzed over hundreds of random games. **This single invariant catches most
  bugs.** If you touch anything that moves cards, this is your safety net.
- **Replay determinism** — same seed + answers → identical event log.
- **Redaction never leaks a hand** — fuzzed.
- **Per-card tests** — `test_abilities.py` (deploy abilities, blocks, steal, nested
  turn) and `test_scoring.py` (bonus clauses, wildcards, ⏰ phase). Each is written from
  the card text and doubles as the spec.

Beyond tests: `uv run python -m red_rising.engine.random_driver --seed 1` plays a whole
game to a final score, and `random_driver.play_random_game` is what the fuzz tests use.
For end-to-end UI, run the server and drive two browser sessions.

`uv run ruff check .` must be clean.

---

## 9. Key decisions & rationale (quick reference)

| Decision | Why | Don't |
|---|---|---|
| Per-card Python scripts, not a rules DSL | 98/107 deploy abilities are structurally unique | Build a config-driven rules language |
| Pure, deterministic engine (no I/O/async) | Free replay, undo, persistence, fuzzing, bot | Add I/O or serialize the live generator |
| Turn flow is itself a generator/script | One machine for turns + card abilities | Split into two engines |
| Pending decision = the legal moves | No separate move generator to maintain | Write a parallel `legal_actions` |
| Persistence = seed + specs + answer log | Rebuild by replay; no snapshot format | Persist board state |
| Blocks in primitives, not card scripts | 5 block cards → 2 semantics; cards stay clean | Re-implement blocking per card |
| Redaction: opponents carry `hand_count` | Leaking a hand is structurally impossible | Put opponent `hand` in the view |
| `sessionStorage` for creds | Per-tab; the link is the credential | Switch to localStorage |
| Python 3.13 (pinned `<3.14`) | pydantic/pyarrow wheel coverage | Bump to 3.14 without checking wheels |
| Data: parquet → validated `cards.json` | Engine reads JSON; pandas quarantined to build step | Read the parquet at runtime |

---

## 10. Traps & non-obvious things

- **`Color` is a `StrEnum`.** `isinstance(a_color, str)` is `True`. `scoring/context.py`
  splits color vs name targets explicitly because of this; if you write similar
  membership logic, remember it.
- **Location stack orientation:** the **top** card is the **last** element of
  `LocationStack.cards`. The UI renders covered cards *above* and the full top card
  *below* them (matching the physical overlap) — this visually inverts intuition and
  caused real confusion during development. "Deployed on top of X" means X was the
  previous top, i.e. `stack.below(source)`.
- **`under_at_deploy` is captured once**, before the ability runs. Use it (not a live
  lookup) for "if you deployed on/over a …" conditions.
- **`choose_*` helpers auto-resolve** 0 or 1 candidates without yielding a decision.
  This affects how many answers a scripted test must supply — a sole opponent or a
  single legal card is chosen for you.
- **`trigger_deploy` / `endgame_phase` accept plain OR generator functions.** Keep a
  card script plain if it has no player choice; make it a generator only when it yields.
- **Regenerate `cards.json` after editing the parquet:**
  `uv run python -m red_rising.data.build_cards`. A test guards against staleness
  (`test_carddefs.py::test_cards_json_is_current`).
- **Markdown anchors slugify card *names*, not ids** (`#the-jackal` → card id `jackal`;
  colors are plural, `#golds`). `data/parse.py:AnchorResolver` handles this.
- **One server instance only.** Live games are held in memory keyed by game id; all
  traffic for a game must reach the same process. `fly.toml` pins a single machine.
  Games survive restarts (replayed from SQLite), but horizontal scaling would need a
  shared store or sticky routing.

---

## 11. Known simplifications (places a rules purist might tighten)

These are intentional, documented approximations — good first issues if you want the
last few percent of fidelity. Each is localized to one card's script.

- **Firewall Expert** (`tier2.py`): "place 1 of the top 3 face down at the top of each
  location" is implemented as placing each of 3 revealed cards face-down on a distinct
  chosen location. The exact distribution is arguable.
- **"reveal 2 and place under this card in any order"** (Administrator et al.): placed
  in revealed order; the "any order" micro-choice is skipped.
- **End-of-game abilities resolve in hand order**, not a player-chosen order among
  their own ⏰ abilities (rarely more than one per player, so it almost never matters).
- **Artisan Chef's "ignore lost points from Golds"** is implemented as: clamp any Gold
  card's *net* negative bonus to 0. A literal reading might clamp per-clause.
- **Wildcard "for each by *name*"** could double-count an Orange renamed to a character
  you also hold; binary "if with X" is unaffected. No current card exercises the edge.

---

## 12. Extension points (deliberately left cheap)

- **AI opponent.** The engine already exposes every legal move as the pending
  decision's options, and offers a cheap deep-copy (pydantic) plus deterministic
  replay. A greedy bot is a few hundred lines against `random_driver`'s shape; MCTS
  would need determinization for the hidden hands.
- **Card art.** `CardDef.art_url` exists and `CardView` reserves nothing yet but reads
  from the card def — add the field to the pipeline and render it. 
- **3–6 players.** The engine fully supports 2–6 (fuzzed). The lobby and table UI are
  tuned for 2 but the components are generic; opening it up is mostly lobby UX.
- **Real accounts / matchmaking.** Currently link + token. Would replace the auth in
  `app/store.py`/`server.py` and add a users table.
- **openapi-typescript** to generate `web/src/types.ts` from the FastAPI schema instead
  of hand-maintaining it.

---

## 13. Provenance & scope

Built from a personal copy of the game for private two-player use. Card text lives in
`red_rising_characters.parquet`; the rules digest is `red-rising-rulebook.md`. *Red
Rising* is © Pierce Brown; tabletop rights Stonemaier Games. 

---

## 14. Where to start if you're new here

1. Run it: `uv run pytest` (green?), then `uv run python -m red_rising.engine.random_driver --seed 1`.
2. Read `engine/rules.py:play_turn` and `engine/engine.py:_run` — that's the whole control loop.
3. Read three card scripts of increasing complexity: `deanna` (tier0, plain),
   `cassius` (tier1, conditional self-banish), `tactus` (tier3, opponent + steal + block).
4. Read `app/views.py:redact` and `app/store.py` — the entire server-side story.
5. Make a change, keep card conservation and the redaction fuzz test green.
