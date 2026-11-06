# 006-scoring: Points for intercepts, correct survival bonus, live HUD score

## Problem
The score never changes during play. When a player explosion destroys an enemy missile,
`check_collisions()` awards nothing. `ScoreSystem.add_survival_time(dt)` adds `int(dt)`,
which is 0 for every real frame (dt is at most 0.16 s), so surviving earns nothing either.
The HUD redraws `SCORE: …` every frame, but the value is always 0. The text is also
left-anchored at `SCREEN_WIDTH - 220`, so a large score would run off the right edge.
There is also a dead `MainGame.handle_score_updates()` that calls `pygame.time.get_ticks()`
and would double-count time if anything called it.

## Scope
- **Intercept points.** In `MainGame.check_collisions()`, each time a player explosion
  destroys an incoming missile (the existing `incoming.destroy()` branch), call
  `self.score_system.add_missile_hit(MISSILE_INTERCEPT_POINTS)`. A missile is counted once
  only. The existing `if incoming.is_destroyed: continue` guard already skips missiles that
  are dead, and it must still run before the radius check.
  - Non-player explosions award nothing (they destroy nothing today).
  - A missile destroyed by hitting a building awards nothing. The building check runs first
    in `check_collisions()`, so a missile that hits a building and also sits inside a player
    blast in the same call gives 0 points.
  - Missiles that fall off the bottom of the screen award nothing.
- **`add_missile_hit`.** The default for `points` becomes `MISSILE_INTERCEPT_POINTS`. It still
  adds `points` to `score` and increments `total_missiles_hit` by 1.
- **Survival time.** Rewrite `ScoreSystem.add_survival_time(dt)` so fractional seconds add up
  across frames:
  - If `dt <= 0`, do nothing.
  - Otherwise, `before = int(self.time_survived)`, then `self.time_survived += dt`, then
    `self.score += (int(self.time_survived) - before) * SURVIVAL_POINTS_PER_SECOND`.
  - `time_survived` is a float. It starts at `0.0` in `__init__` and `reset()` sets it back
    to `0.0`.
  - `MainGame.update(dt)` keeps its one call to `add_survival_time(dt)`. Survival therefore
    accrues only while `update()` runs, which is only in `STATE_PLAYING`.
- **HUD.**
  - Add `MainGame.hud_score_text()`, which returns `f"SCORE: {self.score_system.score:,}"`.
  - `draw()` renders that text in `COLOR_YELLOW` with the existing 36 pt font. The text is
    right-aligned so its rect's `topright == (SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN)`,
    replacing the fixed `(SCREEN_WIDTH - 220, 10)` position.
  - Order within a frame stays `update` → `check_collisions` → `draw`, so an intercept shows
    on the HUD in the frame it happens.
- **Dead code.** Delete `MainGame.handle_score_updates()` and the
  `total_missile_hits_this_level` attribute, which only that method used. After this,
  `get_ticks` no longer appears anywhere in `systems/game_loop.py`.
- **Constants** (new `# Scoring` section in `game/constants.py`):
  - `MISSILE_INTERCEPT_POINTS = 10`. This matches GAME_DESIGN.md §8, "Defense Missile Hit
    Enemy: +10".
  - `SURVIVAL_POINTS_PER_SECOND = 1`. This matches §8, "+1 point per second survived".
  - `HUD_MARGIN = 10`, the gap in px between the HUD score and the top and right screen edges.
- **README.** In Gameplay, add one sentence: each enemy missile destroyed by your explosion
  scores `MISSILE_INTERCEPT_POINTS` (10), and every full second survived scores 1.
- **Tests.** Add a new file `tests/test_scoring.py`.

## Out of scope
- Points for buildings. `add_building_destroyed()` stays uncalled. Awarding points when the
  player *loses* a building (GAME_DESIGN.md §8) is a design question for a later job.
- Score multipliers, chain/combo bonuses, and per-wave bonuses.
- The unused `ScoreDisplay` class in `systems/score.py`: leave it unchanged, don't wire it in
  and don't delete it.
- The HUD sub-line with missiles/buildings counts, the kill feed, and floating "+10" popups.
- Any change to `save_high_score()`, `load_high_score()`, the `config.json` format, or the
  game-over and menu screens. They already read `score_system.score`.
- Resetting the launcher cooldown on restart (the next backlog item).
- Updating `GAME_DESIGN.md`.

## Acceptance criteria
Unless a criterion says otherwise, tests use the `main_game` fixture (`STATE_PLAYING`, 8
buildings, no random spawns, `CONFIG_PATH` under `tmp_path`) and `random.seed(0)`. A
**parked missile** is an `IncomingMissile` with `position` set to the given point and
`velocity = Vector2(0, 0)`, as in `tests/test_missiles_explode.py`. A **player blast** is
`game.explosion_pool.get_explosion(400, 300, is_player=True)`, appended to `game.explosions`
and advanced with `update(0.25)` to radius 40.

1. [test] **One intercept scores once.**
   - Setup: a player blast and one parked missile at (410, 300).
   - `check_collisions()` gives `score == MISSILE_INTERCEPT_POINTS` (10) and
     `total_missiles_hit == 1`.
   - Calling `check_collisions()` 4 more times, with the blast still active, leaves both
     values unchanged.
2. [test] **Several intercepts in one blast.**
   - Setup: a player blast and parked missiles at (400, 300), (430, 300) and (400, 335), all
     inside the blast, plus one at (450, 300), outside it.
   - One `check_collisions()` gives `score == 3 * MISSILE_INTERCEPT_POINTS` and
     `total_missiles_hit == 3`. The outside missile is not destroyed.
3. [test] **Overlapping blasts don't double-count.** Two player blasts at (400, 300) and
   (420, 300), both advanced to radius 40, and one parked missile at (410, 300). One
   `check_collisions()` gives `score == 10` and `total_missiles_hit == 1`.
4. [test] **No points for other ways a missile dies.** Each case starts at `score == 0`, and
   after it `score == 0` and `total_missiles_hit == 0`:
   - **Non-player blast:** a blast from `get_explosion(400, 300)` at radius 40, with a
     parked missile at (410, 300). Call `check_collisions()`.
   - **Building impact:** a parked missile at the centre of `game.buildings[0]`. Call
     `check_collisions()`. The building's `health_current` becomes 66.
   - **Impact inside a player blast:** a parked missile at the centre of `game.buildings[0]`,
     plus a player blast at that same centre at radius 40. Call `check_collisions()`. The
     missile is destroyed by the impact, and the building's `health_current` becomes 66.
   - **Off-screen:** a missile at `(400, SCREEN_HEIGHT + 60)` with zero velocity. Run
     `update(DT_DEFAULT)` and `check_collisions()` once. The missile is gone from
     `incoming_missiles`. Ignore the survival bonus here: `int(1/60) == 0`, so it adds
     nothing.
5. [test] **Survival time accumulates across frames.** On a bare `ScoreSystem()`, with
   `CONFIG_PATH` patched to `tmp_path`:
   - 59 calls of `add_survival_time(DT_DEFAULT)` leave `score == 0`.
   - 2 more calls (61 in total) give `score == 1`.
   - On a second fresh instance, 3599 calls give `score == 59`, and 2 more (3601) give
     `score == 60`. In every case `time_survived == pytest.approx(n * DT_DEFAULT)`.
6. [test] **Large and uneven dt, exact values.** On a fresh `ScoreSystem()`:
   - `add_survival_time(0.25)` three times gives `score == 0`.
   - A fourth call gives `score == 1`.
   - `add_survival_time(2.5)` gives `score == 3`.
   - `add_survival_time(0.5)` gives `score == 4` and `time_survived == 4.0`.
7. [test] **Non-positive dt is ignored.** `add_survival_time(0.0)` and
   `add_survival_time(-1.0)` leave both `score` and `time_survived` unchanged, starting
   from `time_survived == 0.75` and `score == 0`.
8. [test] **Survival through the game.** `game.update(DT_DEFAULT)` called 121 times gives
   `game.score_system.score == 2`, with no intercepts. The total also equals
   `int(game.game_time)`.
9. [test] **Paused and menu states don't score.**
   - Monkeypatch `utils.timer.time` with a fake clock, as in `tests/test_game_states.py`
     criterion 12. Set `game.state = STATE_PAUSED`. Fake `handle_events` so that calls 1–10
     each advance the clock by 1.0 s and return `{}`, and call 11 returns `{"quit": True}`.
   - Run `start_game_loop()`. Afterwards, `score == 0` and `time_survived == 0.0`.
   - Repeat with `game.state = STATE_GAME_OVER` and the score preset to 50. It stays 50.
10. [test] **Restart resets scoring.**
    - Score one intercept, then call `add_survival_time(0.75)`. Mark all buildings
      destroyed, then call `check_collisions()` and `check_game_over()`.
    - `handle_actions({"start": True})` gives `score == 0`, `total_missiles_hit == 0` and
      `time_survived == 0.0`.
    - Then `add_survival_time(0.5)` gives `score == 0`. This proves the 0.75 s did not carry
      over.
11. [test] **High score includes the new points.**
    - Score one intercept (10), then call `game.update(0.5)` 4 times (+2 survival, 12 in
      total).
    - Mark all buildings destroyed, then call `check_collisions()` and `check_game_over()`.
    - `json.loads(config.json) == {"high_score": 12}` and
      `game.score_system.high_score == 12`.
12. [test] **HUD text is live.**
    - `game.hud_score_text() == "SCORE: 0"` at start.
    - After the criterion-1 intercept, it is `"SCORE: 10"`.
    - With `score = 1234567` it is `"SCORE: 1,234,567"`.
    - Render `game.draw()` at score 0 and again at score 10. The pixels in the rect
      `(SCREEN_WIDTH - 300, 0, 300, 50)` differ between the two frames.
13. [test] **HUD stays on screen and right-aligned.**
    - Set `score = HIGH_SCORE_MAX`, with no missiles or explosions, and call `draw()`.
    - At least one pixel in rows 10–45, columns `SCREEN_WIDTH - 300` to
      `SCREEN_WIDTH - HUD_MARGIN - 1`, equals `COLOR_YELLOW`.
    - Every pixel in rows 0–49, columns `SCREEN_WIDTH - HUD_MARGIN` to `SCREEN_WIDTH - 1`,
      has red channel `== COLOR_BLUE[0]`. The sky gradient keeps red at `COLOR_BLUE[0]`, so
      any text pixel there would raise it.
14. [test] **Dead code gone.** `not hasattr(MainGame, "handle_score_updates")`, `"get_ticks"
    not in inspect.getsource(systems.game_loop)`, and `"total_missile_hits_this_level" not in
    inspect.getsource(systems.game_loop)`.
15. [test] All existing tests pass unchanged. The full suite passes with the README command,
    and the real `config.json` is byte-for-byte unchanged.
16. [visual] **Mid-play HUD.** Start a game, intercept one parked missile with a player
    blast, then run 61 `update(DT_DEFAULT)` frames, calling `check_collisions()` each frame,
    and render `draw()`. The top-right corner shows `"SCORE: 11"` in `COLOR_YELLOW`. Its
    right edge is about `HUD_MARGIN` px from the screen edge and its top about `HUD_MARGIN`
    px down. It doesn't overlap the launcher or the explosion.
17. [visual] **Large score.** With `score = 123456789`, `draw()` shows `"SCORE: 123,456,789"`
    fully visible top-right. No characters are clipped at the right edge.

## Touch points
- `systems/score.py`:
  - `ScoreSystem.__init__` and `reset()`: set `time_survived = 0.0`.
  - `add_missile_hit()`: default `points=MISSILE_INTERCEPT_POINTS`.
  - `add_survival_time()`: rewrite as above.
- `systems/game_loop.py`:
  - `check_collisions()`: one `add_missile_hit(MISSILE_INTERCEPT_POINTS)` call in the
    player-explosion branch.
  - New `hud_score_text()`.
  - `draw()`: right-aligned HUD using `HUD_MARGIN`.
  - Delete `handle_score_updates()` and `total_missile_hits_this_level`.
- `game/constants.py`: a new `# Scoring` section with `MISSILE_INTERCEPT_POINTS = 10`,
  `SURVIVAL_POINTS_PER_SECOND = 1` and `HUD_MARGIN = 10`.
- `README.md`: one Gameplay sentence.
- `tests/test_scoring.py` (new).

Expected diff: about 40 lines of game code and about 180 lines of tests, under 300 in total.
Use shared helpers (a parked-missile factory, a player-blast factory, a fake-clock loop
driver) and parametrise criterion 4's cases.

## Notes for reviewers
- **code:**
  - Check that the intercept award sits inside the `incoming.destroy()` branch, after the
    `is_destroyed` guard, so a missile can't score twice across overlapping blasts or later
    frames.
  - `add_survival_time()` must not round or truncate each frame. Only the difference between
    `int(time_survived)` before and after is awarded. Float drift over 3600 frames of
    `DT_DEFAULT` is about 1e-13, so criterion 5 checks just off each whole second (59/61,
    3599/3601), never exactly on it.
  - `update()` must still call `add_survival_time` exactly once per frame. The deleted
    `handle_score_updates()` must not be "rescued" into the loop.
  - The HUD position must come from `get_rect(topright=...)` and not from a hard-coded
    width.
- **security:** No new file or network I/O. `save_high_score()` is still called only from
  `check_game_over()`. The score can now grow during play, but `save_high_score()` and the
  `HIGH_SCORE_MAX` check on load are unchanged. Reaching `HIGH_SCORE_MAX` through play
  would take decades. Tests must patch `CONFIG_PATH` before building a `ScoreSystem` or
  `MainGame`, and the `utils.timer.time` monkeypatch must stay scoped to its test.
- **ux:**
  - 10 points per intercept against 1 per second means a run's score is driven mostly by
    intercepts. That matches GAME_DESIGN.md §8.
  - Losing a building costs nothing on the scoreboard (out of scope). Flag it if that feels
    wrong in play.
  - The score should visibly tick up once per second during play and jump by 10 on each
    intercept.
- **ui:** Check frames 16 and 17.
  - The HUD keeps the same font and `COLOR_YELLOW` and moves only from left-anchored to
    right-anchored.
  - Confirm it stays legible over the light top of the sky gradient. It should not collide
    with explosions near the top-right in normal play.
