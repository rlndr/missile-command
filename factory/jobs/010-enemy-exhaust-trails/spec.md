# 010-enemy-exhaust-trails: Exhaust trails behind enemy missiles

## Problem
Each enemy missile is drawn as a lone red dot (`MainGame.draw_missile`). It is hard to see which
way a missile is going or which building it is heading for until it has moved a fair way, and
the screen looks bare next to the original game. GAME_DESIGN.md §10 asks for "particle trails
on missiles", but no missile keeps any history of where it has been.

## Scope
- **Trail history on `IncomingMissile`** (`entities/missile.py`).
  - New attribute `trail`: past positions, oldest first. It may be a `list` or a
    `collections.deque(maxlen=ENEMY_TRAIL_MAX_POINTS)`. It is empty when the missile is built.
  - In `update(dt)`, **before** moving: if the missile is not destroyed, and `trail` is empty
    or the current position is at least `ENEMY_TRAIL_SPACING` px from `trail[-1]`, append a
    **copy** of the current position (`pygame.math.Vector2(self.position)`). Then move as
    today. If the trail now holds more than `ENEMY_TRAIL_MAX_POINTS` samples, drop the oldest.
  - Recording before the move means the head is always ahead of the newest sample once the
    missile has moved. Sampling by distance (not once per frame) keeps the trail about the same
    length in px at 30, 60 or 144 fps.
  - A destroyed missile's `update()` leaves `trail` unchanged.
- **`IncomingMissile.trail_segments()`** (new). Returns a list of `(start, end, color)` tuples,
  ordered from the head back to the tail. There is one tuple per sample, so `len == len(trail)`:
  - segment 0 runs from `self.position` to `trail[-1]`;
  - segment k runs from `trail[-k]` to `trail[-1-k]`, so each segment starts where the one
    before it ended;
  - with `n = len(trail)`, segment k's colour is a per-channel linear blend from
    `ENEMY_TRAIL_HEAD_COLOR` (k = 0) to `ENEMY_TRAIL_TAIL_COLOR` (k = n - 1), using
    `f = k / (n - 1)` (or `f = 0` when `n == 1`). Each channel is rounded to an int in 0–255.
  - With an empty trail it returns `[]`.
- **`IncomingMissile.draw_trail(screen)`** (new). Draws each segment from `trail_segments()`
  with `pygame.draw.line(screen, color, start, end, ENEMY_TRAIL_WIDTH)`, **oldest segment
  first**, so the brighter, newer colour wins where two segments meet. It does not draw the
  missile head. With an empty trail it draws nothing.
- **`MainGame.draw()`** (`systems/game_loop.py`). New draw order:
  launcher → buildings → **enemy trails** → defense missiles → enemy heads → explosions → HUD.
  - Trails are drawn for every incoming missile that is not destroyed. All trails are drawn
    before any head, so no trail ever covers a red head or a yellow defense missile.
  - The existing defense-missile and enemy-head loops stay as they are; only the new trail
    loop is added, before the defense-missile loop.
- **New constants** in `game/constants.py`, in a new `# Enemy missile exhaust trail` block
  placed right after the `# Missile speeds` block (see Touch points).
- **README.** Add one bullet at the end of "Features": enemy missiles leave a short exhaust
  trail that fades from orange to grey smoke. Do **not** edit the "Gameplay" paragraph
  (job 009 rewrites the launcher sentence there).
- **Tests.** Add a new file, `tests/test_enemy_exhaust_trails.py`. Do not edit existing test files.

## Out of scope
- Any change to `DefenseMissile`, `DefensiveBase`, the launcher position, or the
  `LAUNCHER_*` constants. Job 009-bottom-launcher is moving the launcher in parallel. Trails
  on defense missiles are a possible follow-up once 009 has landed.
- Trails or smoke that linger after a missile is destroyed or goes off screen. The trail
  disappears along with the missile.
- Particle effects, alpha blending or per-pixel fading. Trails are solid lines whose colour
  steps from head to tail.
- Changing enemy speed, spawn logic, collision, scoring or screen shake. `draw()` works out
  a shake offset and never uses it; this job leaves that as it is.
- Drawing trails on the start, pause or game-over screens. Those screens don't draw
  missiles today.
- GAME_DESIGN.md edits.

## Acceptance criteria
Tests patch `systems.score.CONFIG_PATH` to a file under `tmp_path` before building any
`MainGame` (the `main_game` fixture already does this). Terms used below:
- A **controlled missile** is `m = IncomingMissile(Vector2(400, 500))`, then
  `m.position = Vector2(400, 100)`, `m.velocity = Vector2(0, INCOMING_MISSILE_SPEED)` and
  `m.trail.clear()`. It flies straight down at 200 px/s, so `update(0.05)` moves it exactly
  10 px.
- A **60-frame game** is the `main_game` fixture with `game.incoming_missiles = [m]` for a
  controlled missile `m`, after 60 rounds of `update(DT_DEFAULT)` + `check_collisions()`.
  The head is then at about (400, 300), the newest sample at about y = 293.3 and the oldest
  at about y = 220.
- **Surface draw** means: make a `pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))`, fill it with
  `COLOR_BLACK`, call `m.draw_trail(surface)`, then read pixels with `surface.get_at((x, y))[:3]`.
- **Sky at y** means `game.screen.get_at((300, y))[:3]`. The background gradient only
  changes with y, and nothing else is drawn at x = 300 in these tests.
- Compare float positions with `pytest.approx`.

1. [test] **Constants.** `ENEMY_TRAIL_SPACING == 6`, `ENEMY_TRAIL_MAX_POINTS == 12` and
   `ENEMY_TRAIL_WIDTH == 2`, all ints and all positive. `ENEMY_TRAIL_HEAD_COLOR == COLOR_ORANGE`
   and `ENEMY_TRAIL_TAIL_COLOR == COLOR_GRAY`. Both are 3-tuples of ints in 0–255, different
   from each other, and both different from `COLOR_RED` (the head colour).
2. [test] **Empty at birth.** A freshly built `IncomingMissile(Vector2(400, 500))` has
   `len(trail) == 0`, `trail_segments() == []`, and surface draw leaves every pixel
   `COLOR_BLACK`.
3. [test] **Sampling.** Controlled missile, `update(0.05)` six times. `trail` holds exactly 6
   samples at y = 100, 110, 120, 130, 140, 150 (all x = 400), oldest first, and the head is
   at (400, 160). No sample `is` `m.position`, and no two samples are the same object
   (pygame's `Vector2 +=` works in place, so storing the position itself would make every
   sample follow the head).
4. [test] **Spacing.** Controlled missile, `update(0.01)` (2 px per step) ten times. `trail`
   holds samples at y = 100, 106, 112, 118 only (a new sample once the missile is at least
   6 px past the last one), and the head is at y = 120.
5. [test] **Cap.** Controlled missile, `update(0.05)` twenty times. `len(trail) == 12`,
   `trail[0]` is at y = 180, `trail[-1]` is at y = 290, and the head is at y = 300.
6. [test] **About the same length at any frame rate.** For each `dt` in `1/30`, `DT_DEFAULT`
   and `1/144` (parametrised): a controlled missile with `m.position = Vector2(400, 0)` runs
   `round(2.0 / dt)` updates. Then `len(trail) == 12` and
   `72 <= m.position.distance_to(trail[0]) <= 90`.
7. [test] **Stopped when destroyed.** Controlled missile, `update(0.05)` three times, then
   `destroy()`, then `update(0.05)` five more times. `trail` holds the same 3 samples as
   before `destroy()`, and the head has not moved.
8. [test] **Segments.** Controlled missile after six `update(0.05)` calls (as in 3).
   `trail_segments()` has 6 entries. Segment 0 runs from (400, 160) to (400, 150). Each
   segment's start equals the previous segment's end, and the last segment ends at (400, 100).
   Segment 0's colour is `ENEMY_TRAIL_HEAD_COLOR` and segment 5's is `ENEMY_TRAIL_TAIL_COLOR`.
   Every colour is a 3-tuple of ints in 0–255. From segment 0 to segment 5, each channel moves
   steadily from the head value to the tail value: never backwards, never past either end.
   A missile with exactly one sample has one segment, coloured `ENEMY_TRAIL_HEAD_COLOR`.
9. [test] **Pixels.** Same missile as 8, surface draw.
   - `(400, 155)` is `ENEMY_TRAIL_HEAD_COLOR`.
   - `(400, 105)` is `ENEMY_TRAIL_TAIL_COLOR`.
   - `(400, 145)` is `trail_segments()[1][2]`.
   - `(400, 95)` (beyond the tail) and `(400, 165)` (beyond the head) are `COLOR_BLACK`.
   - `(397, 130)` and `(403, 130)` are `COLOR_BLACK`, so the line is no wider than
     `ENEMY_TRAIL_WIDTH` allows.
   - No pixel in `Rect(390, 90, 21, 80)` is `COLOR_RED`, because `draw_trail` does not draw
     the head.
10. [test] **Wired into the game frame.** On a 60-frame game, the head is at
    `pytest.approx` (400, 300) and `len(m.trail) == 12`. Then `draw()`. On `game.screen`:
    - `(400, 300)` is `COLOR_RED` (the head is drawn over its own trail);
    - `(400, 290)` is `m.trail_segments()[1][2]`;
    - `(400, 250)` is neither `COLOR_RED` nor the sky at y = 250;
    - `(400, 210)`, above the oldest sample, is the sky at y = 210.
11. [test] **Draw order.** On a 60-frame game, without calling `update()` again: build a
    `DefenseMissile(Vector2(400, 300))`, set its `position = Vector2(400, 250)`, and append it
    to `game.defense_missiles`. Build a second `IncomingMissile`, set its
    `position = Vector2(400, 232)` and `velocity = Vector2(0, 0)`, clear its trail, and append
    it to `game.incoming_missiles`. After `draw()`, `(400, 250)` is `COLOR_YELLOW` and
    `(400, 232)` is `COLOR_RED`. Trails never cover a defense missile or an enemy head.
12. [test] **Destroyed missiles draw no trail.** On a 60-frame game, call `m.destroy()` and
    then `draw()`, without `update()`. `(400, 250)` and `(400, 290)` are the sky at their y.
13. [test] **Pause freezes the trail; restart clears it.** Using `main_game`: controlled
    missile in `game.incoming_missiles`, `update(0.05)` four times. Save
    `[tuple(p) for p in m.trail]`. `handle_actions({"toggle_pause": True})` gives
    `STATE_PAUSED`. Calling `draw_start_screen()` leaves the saved trail unchanged.
    `handle_actions({"toggle_pause": True})` again gives `STATE_PLAYING`, and the trail is
    still unchanged. Then mark every building destroyed, call `check_collisions()` and
    `check_game_over()` (giving `STATE_GAME_OVER`), and `handle_actions({"start": True})`.
    `game.incoming_missiles == []`.
14. [test] **Real spawns.** Using `main_game` with `random.seed(1)`: call
    `game.spawn_incoming_missile()` three times, then `update(DT_DEFAULT)` and
    `check_collisions()` 90 times, and `draw()` once. It does not raise. Every missile still
    in `game.incoming_missiles` has `1 <= len(trail) <= ENEMY_TRAIL_MAX_POINTS`, and every
    sample is inside `Rect(0, -60, SCREEN_WIDTH, SCREEN_HEIGHT + 120)`.
15. [test] **Scope fence.** `inspect.getsource(entities.missile.DefenseMissile)` contains no
    `trail`, and `inspect.getsource(entities.base)` contains no `ENEMY_TRAIL`. `"get_ticks"`
    does not appear in `inspect.getsource(entities.missile)`: the trail follows game time
    (`dt`), not wall time.
16. [test] All existing tests pass unchanged. The full suite passes with the README command,
    and the real `config.json` is byte-for-byte unchanged.
17. [visual] **Mid-flight frame.** Using `main_game` with `random.seed(1)`: three
    `spawn_incoming_missile()` calls, 90 frames of `update(DT_DEFAULT)` + `check_collisions()`,
    then `draw()`. Each red enemy dot has a thin trail about 80 px long reaching back toward
    the top of the screen, along its line of flight. The trail is `COLOR_ORANGE` next to the
    head and fades step by step to `COLOR_GRAY` at the far end. The red heads sit cleanly on
    top of their trails. The launcher, its reload bar and the HUD score look the same as before.
18. [visual] **Trail meets a shot.** Same game as 17: fire with
    `handle_actions({"fire_missile": (x, y)})` at a point just below one enemy head, then run
    20 more frames and `draw()`. The yellow defense missile is drawn over any trail it crosses.
    No trail is drawn over the yellow dot or over an explosion.

## Touch points
- `entities/missile.py`, `IncomingMissile` only:
  - `__init__`: `self.trail` starts empty;
  - `update(dt)`: record a sample before moving, keep at most `ENEMY_TRAIL_MAX_POINTS`;
  - new `trail_segments()`;
  - new `draw_trail(screen)`.
- `systems/game_loop.py`, `MainGame.draw()`: add a loop that calls `draw_trail(self.screen)`
  on each incoming missile that is not destroyed, before the defense-missile loop. Nothing
  else in this file changes.
- `game/constants.py`, new `# Enemy missile exhaust trail` block right after `# Missile speeds`:
  - `ENEMY_TRAIL_SPACING = 6`: minimum px between trail samples.
  - `ENEMY_TRAIL_MAX_POINTS = 12`: samples kept per missile (about 80 px of trail).
  - `ENEMY_TRAIL_WIDTH = 2`: line width in px.
  - `ENEMY_TRAIL_HEAD_COLOR = COLOR_ORANGE`: hot exhaust next to the missile.
  - `ENEMY_TRAIL_TAIL_COLOR = COLOR_GRAY`: cooled smoke at the far end.
  These must be defined after the `COLOR_*` names they use (the colour block is already above
  `# Missile speeds`).
- `README.md`: one new bullet at the end of "Features".
- `tests/test_enemy_exhaust_trails.py` (new).
- Not touched: `entities/base.py`, `DefenseMissile`, `LAUNCHER_*` constants,
  `systems/input_system.py`, `systems/score.py`.

Expected diff: about 40–50 lines of game code and constants, and 200–250 lines of tests.
Parametrise criterion 6. Share a `_controlled_missile()` helper, a 60-frame-game helper and a
surface-draw helper.

## Notes for reviewers
- **code:**
  - Samples must be copies. `GameEntity.apply_velocity` does `self.position += ...`, which
    changes the `Vector2` in place. Appending `self.position` itself would make every sample
    move with the head (criterion 3).
  - Record the sample **before** `apply_velocity`, and only when not destroyed. Recording
    after the move would put a sample on the head and give a zero-length first segment.
  - The cap must hold the whole time (criterion 5). A `deque(maxlen=...)` or a pop of the
    oldest entry are both fine. Don't let the list grow without limit and trim it in `draw()`.
  - Colours come from the two constants by linear blending, not a hard-coded table, and every
    channel is an `int` (pygame rejects floats in some colour paths).
  - Length is set by distance (spacing × max points), not frame count. At very large `dt`
    (the loop caps it at 0.16 s) samples land further apart and the trail gets longer. That is
    acceptable; criterion 6 covers the normal frame rates.
- **merge with 009-bottom-launcher:** 009 is being built in parallel. This job must not touch
  `DefenseMissile`, `DefensiveBase`, the `# Launcher position` constants or the README "Gameplay"
  paragraph. The only shared file is `MainGame.draw()`; this job adds one loop before the
  defense-missile loop. If 009 also edits `draw()`, expect a small, easy merge there and in the
  README "Features" list.
- **security:** No new file, network or config I/O. Tests must patch `CONFIG_PATH` before
  building a `MainGame`. Entity and surface-draw tests need no `MainGame`.
- **performance:** At most 12 short line draws per enemy missile per frame. With the current
  spawn rate (at most one every 2 s) that is negligible.
- **ux:** The trail shows each missile's heading and rough target right after it spawns, so the
  player can pick a target sooner. It must never hide a defense missile, an enemy head or an
  explosion (criterion 11, frame 18).
- **ui:**
  - Check frames 17 and 18. Orange near the head should read as exhaust, fading to grey smoke
    that still shows against the blue sky gradient (`COLOR_GRAY` is (80, 80, 80) on roughly
    (50, 40–100, 200)).
  - The trail should be clearly thinner than the 16 px red head.
  - Trails are drawn above buildings, so a missile diving into a building can draw a few px
    of trail over it in its last frames. That is acceptable and matches the original arcade game.
