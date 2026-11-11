# 003-buildings-game-over: Only enemy hits damage buildings, and the game ends when the city falls

## Problem
The player can't lose, and their own shots wreck the city. In `MainGame.check_collisions()`
the explosion-vs-building loop applies distance-based damage every frame from every active
explosion, player shots included. So a defensive explosion near the skyline destroys
buildings within a few frames, and the damage depends on frame rate. Destroyed buildings
stay in `self.buildings`, so the loop's `if not self.buildings` check never fires and the
game never reaches `STATE_GAME_OVER`. Enemy missiles also keep aiming at buildings that are
already rubble. Finally, the loop calls `save_high_score()` on every frame spent in
`STATE_GAME_OVER` instead of once. That save also does nothing when `config.json` is missing,
never updates the in-memory `high_score`, and can raise on a malformed file.

## Scope
- **Only enemy impacts damage buildings.** Delete the explosion-vs-building loop from
  `check_collisions()`. No explosion, player or enemy, damages buildings any more. A building
  loses health only when an `IncomingMissile` is inside its rect (the existing point-in-rect
  check).
- **Fixed damage per impact.** New `Building.take_impact()` calls
  `take_damage(math.ceil(health_max / damage_threshold))`. For the residential type
  (health 100, threshold 3) that is 34, so exactly 3 impacts destroy a building, as the
  `damage_threshold` comment says. The impact branch in `check_collisions()` calls
  `take_impact()` in place of `take_damage(damage_threshold * 25)`. It still spawns one
  non-player explosion at the missile, destroys the missile and sets
  `shake_intensity = SCREEN_SHAKE_BUILDING_HIT`. It now `break`s after the first building, so
  one missile damages at most one building.
- **Destroyed buildings stop counting.**
  - At the end of `check_collisions()`, `self.buildings` is filtered to buildings that are
    not `is_destroyed`.
  - New read-only property `MainGame.buildings_left` returns the number of buildings in
    `self.buildings` with `is_destroyed == False`.
  - `spawn_incoming_missile()` picks its target only from buildings that are not destroyed.
    If none are standing, it keeps the existing random-ground fallback.
- **Game over.** New `MainGame.check_game_over()`. If `self.state == STATE_PLAYING` and
  `buildings_left == 0`, it switches to `STATE_GAME_OVER` and calls
  `self.score_system.save_high_score()` exactly once. In any other state it does nothing.
  `start_game_loop()` calls it once per playing frame, after `update` / `check_collisions` /
  `draw`. Remove the old `if not self.buildings ...` check and the
  `elif self.state == STATE_GAME_OVER: save_high_score()` branch.
- **`ScoreSystem.save_high_score()` hardening.** A missing file counts as a stored high score
  of 0.
  - When `score` is greater than the stored value, write `{"high_score": score}` into the
    existing JSON object, keeping every other key, or create the file if it is missing.
  - If the file exists but isn't a JSON object, or its `high_score` can't be read with
    `int()`, leave the file byte-for-byte untouched.
  - The method never raises. It catches `OSError`, `ValueError` (which includes
    `JSONDecodeError`) and `TypeError`.
  - Whatever happens to the file, afterwards
    `self.high_score == max(previous self.high_score, self.score)`.
- **Game-over screen shows the high score.** In `draw_start_screen()`, the `STATE_GAME_OVER`
  branch adds a line `f"High Score: {high_score:,}"`. It uses the 36 pt font in
  `COLOR_YELLOW` and is centred at `(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60)`.
  "Press SPACE to Restart" moves down to `SCREEN_HEIGHT // 2 + 110`.
- **README.** Change the "Buildings take damage and are destroyed by explosions" feature
  bullet to say buildings are damaged only by enemy missile impacts (3 hits destroy one).
- **Tests.** New file `tests/test_buildings_game_over.py`.

## Out of scope
- Enemy aim. Missiles target a building's left edge (`position.x`), and
  `IncomingMissile` adds +50 to the target y. Some shots that come in from the left pass
  between buildings and miss. They stay harmless.
- Scoring (backlog item 5). `add_survival_time` still truncates to 0 each frame, so real
  play scores 0 and `save_high_score()` writes nothing in practice yet. Tests set
  `score_system.score` directly. `ScoreSystem.add_building_destroyed` stays unused.
- State flow (backlog item 4): the start screen, ESC pause/resume, and SPACE restarting from
  `STATE_GAME_OVER`. Today restart rebuilds buildings but leaves the state at
  `STATE_GAME_OVER`. The SPACE-during-play branch that deletes standing buildings also
  stays.
- Splash damage from enemy impacts to neighbouring buildings, rubble/smoke visuals for
  destroyed buildings, a "buildings left" HUD counter, and a "NEW HIGH SCORE" banner.
- `load_high_score()` hardening, and `spawn_new_building()` (never called).
- Updating `GAME_DESIGN.md`.

## Acceptance criteria
Unless a criterion says otherwise, tests use the `main_game` fixture (8 residential
buildings, no random spawns, `CONFIG_PATH` under `tmp_path`), `random.seed(0)` and
`DT_DEFAULT`. An **impact on building `b`** means:
1. Append an `IncomingMissile(Vector2(b.position))`.
2. Set its `position` to `b.position + Vector2(b.width / 2, b.height / 2)` and its
   `velocity` to `Vector2(0, 0)`.
3. Call `game.check_collisions()`.

Where a test counts saves, `game.score_system.save_high_score` is monkeypatched with a
counting wrapper.

1. [test] **Three hits per building:** a fresh `Building(30, 540)` has `health_current`
   100, 66, 32, 0 after 0, 1, 2, 3 calls to `take_impact()`. `is_destroyed` is `False` after
   2 calls and `True` after 3.
2. [test] **Impact through the game:** one impact on `buildings[0]`. Afterwards:
   - the missile `is_destroyed`;
   - `buildings[0].health_current == 66`, and the other 7 buildings are at 100;
   - `game.shake_intensity == SCREEN_SHAKE_BUILDING_HIT`;
   - `game.explosions` holds exactly one explosion, with `is_player is False`.
3. [test] **The impact explosion adds no damage:** continuing from 2, run 60 frames of
   `update(DT_DEFAULT)` + `check_collisions()`. `buildings[0].health_current` is still 66.
4. [test] **Player explosions never damage buildings:** append three player explosions
   from `game.explosion_pool.get_explosion(x, y, is_player=True)`:
   - one at `buildings[0].position` (top-left corner);
   - one at `buildings[0]`'s centre;
   - one at `buildings[1]`'s centre.

   Run 60 frames of `update(DT_DEFAULT)` + `check_collisions()`, which covers each
   explosion's whole 0.8 s life. All 8 buildings still have
   `health_current == health_max`, `len(game.buildings) == 8` and
   `game.buildings_left == 8`.
5. [test] **One building per missile:** set `buildings[1].position` to a copy of
   `buildings[0].position` so the two overlap, then do one impact on `buildings[0]`.
   Exactly one of the two buildings has `health_current == 66` and the other is at 100.
6. [test] **Destroyed buildings leave the list:** do three impacts on `buildings[0]`
   (`b0`), each with a new missile and its own `check_collisions()` call. After the third:
   - `b0.is_destroyed`;
   - `b0 not in game.buildings`;
   - `len(game.buildings) == 7` and `game.buildings_left == 7`.

   A fourth stationary missile at `b0`'s old centre is **not** destroyed by
   `check_collisions()`, and no explosion is added.
7. [test] **`buildings_left` counts only standing buildings:** set `is_destroyed = True`
   directly on `buildings[0]` and `buildings[3]`, without calling `check_collisions()`.
   `game.buildings_left == 6` and `len(game.buildings) == 8`.
8. [test] **Spawns target standing buildings only:** mark `buildings[0..6]` destroyed
   directly (no filtering) and call `game.spawn_incoming_missile()` 20 times. Every spawned
   missile has `target.x == game.buildings[7].position.x` (590).
9. [test] **The city redraws without the destroyed building:**
   - Before any hit, `game.draw()` gives
     `game.screen.get_at((60, 560))[:3] == COLOR_GRAY`. (60, 560) is the centre of
     `buildings[0]` and isn't on a window.
   - Destroy `buildings[0]` with three impacts.
   - Run 60 `update(DT_DEFAULT)` calls so the impact explosions expire, then `draw()`.
   - `draw()` doesn't raise, and the pixel at (60, 560) is no longer `COLOR_GRAY`.
10. [test] **No game over while a building stands:** destroy buildings 0–6 by impacts
    (3 each). `check_game_over()` leaves `game.state == STATE_PLAYING`, and the save count
    is 0.
11. [test] **Game over when the last building falls:**
    - Continuing from 10, set `game.score_system.score = 120`.
    - Do three impacts on the last building, then call `check_game_over()`.
    - `game.state == STATE_GAME_OVER` and `game.buildings_left == 0`.
    - `tmp_path / "config.json"` now exists and parses to `{"high_score": 120}`.
    - `game.score_system.high_score == 120`.
12. [test] **Saved exactly once:** with all buildings destroyed (`is_destroyed = True`,
    then `check_collisions()`), call `check_game_over()` 5 times. The state is
    `STATE_GAME_OVER` and the save count is 1.
13. [test] **No game over outside play:** set `game.state = STATE_PAUSED` and destroy all
    buildings. `check_game_over()` leaves the state `STATE_PAUSED` and the save count is 0.
14. [test] **The real loop saves once:** monkeypatch `game.handle_events` with a fake.
    - Call 1 sets `is_destroyed = True` on every building in `game.buildings` and returns
      `{}`.
    - Calls 2–9 return `{}`.
    - Call 10 returns `{"quit": True}`.

    Run `game.start_game_loop()`. It returns, `game.state == STATE_GAME_OVER`, and the save
    count is exactly 1. Before this job the state stayed `STATE_PLAYING`. The old per-frame
    branch would have saved on every frame spent in game over.
15. [test] **`save_high_score` file handling:** each case builds a `ScoreSystem` with
    `systems.score.CONFIG_PATH` monkeypatched to a path under `tmp_path`, set before the
    file is written.
    - (a) The file is the real config's keys with `high_score: 50`, and `score = 120`.
      After the save, `high_score` is 120 in the file and every other key keeps its value.
    - (b) The file has `high_score: 200` and `score = 120`. The file bytes are unchanged.
    - (c) The file contains each of these: `{not json`, `[1, 2]`, `{"high_score": "abc"}`.
      With `score = 120`, there is no exception and the file bytes are unchanged.
    - (d) `CONFIG_PATH` points to a directory. There is no exception.
    - (e) The file is missing and `score = 0`. No file is created.
    - In every case, `score_system.high_score == max(previous high_score, score)`
      afterwards.
16. [test] **Game-over screen draws:** with `game.state = STATE_GAME_OVER`,
    `game.draw_start_screen()` doesn't raise.
17. [test] `tests/test_screen_shake.py` and `tests/test_missiles_explode.py` pass
    unchanged. The full suite passes with the README command, and the real `config.json` is
    byte-for-byte unchanged afterwards.
18. [visual] **City after a loss:** save the criterion 9 frame after destruction. It shows
    7 grey (`COLOR_GRAY`) buildings along the bottom, an empty sky-gradient gap where the
    leftmost building stood (x 30–90), and no explosion rings.
19. [visual] **A player shot over the city:**
    - Put a player explosion at `buildings[2]`'s centre (220, 560) and run 30 frames of
      `update(DT_DEFAULT)` + `check_collisions()`.
    - Save frame A: the explosion rings overlap the building.
    - Run 30 more frames and save frame B: `buildings[2]` is fully drawn with white windows
      and no health bar (full health), and all 8 buildings are present.
20. [visual] **Game-over screen:** set `score_system.score = 120`, end the game as in
    criterion 11, call `draw_start_screen()` and save the frame. From top to bottom it shows:
    - "GAME OVER" in `COLOR_RED`;
    - "Final Score: 120" in `COLOR_YELLOW`;
    - "High Score: 120" in `COLOR_YELLOW`;
    - "Press SPACE to Restart" in `COLOR_WHITE`.

    All four lines are horizontally centred and none overlap.

## Touch points
- `entities/building.py`: new `Building.take_impact()`. It needs `import math`.
- `systems/game_loop.py`:
  - `check_collisions()`: the impact branch uses `take_impact()` and `break`s; delete the
    explosion-vs-building loop; filter `self.buildings` at the end.
  - New `buildings_left` property.
  - `spawn_incoming_missile()`: choose from standing buildings only.
  - New `check_game_over()`.
  - `start_game_loop()`: call `check_game_over()` after the playing frame; remove the
    per-frame save branch and the `if not self.buildings` check.
  - `draw_start_screen()`: the game-over high score line and the moved restart line.
- `systems/score.py`: `save_high_score()`.
- `README.md`: the Features bullet.
- `tests/test_buildings_game_over.py` (new).
- `game/constants.py`: no new constants. Damage per hit comes from the existing
  `BUILDING_TYPES[...]["health_max"]` and `["damage_threshold"]`. Use the existing
  `STATE_*`, `SCREEN_SHAKE_BUILDING_HIT`, `COLOR_GRAY`, `COLOR_RED`, `COLOR_YELLOW` and
  `COLOR_WHITE`.

Expected diff: about 70 lines of game code and about 220 lines of tests. Keep the test file
compact, using shared helpers for "impact on building" and the save counter. The last job
escalated on size.

## Notes for reviewers
- **code:**
  - `buildings_left` must count `is_destroyed`, not `len(self.buildings)`, because criterion
    7 marks buildings destroyed before the list is filtered.
  - `check_game_over()` must be the only place that switches to `STATE_GAME_OVER` and the
    only caller of `save_high_score()`. Grep for any other caller.
  - Filter `self.buildings` after the impact loop, not while iterating it.
  - No leftover use of `EXPLOSION_MAX_RADIUS` for building damage, and no unused locals left
    from the deleted loop.
  - Criterion 14 drives the real `start_game_loop()` through a fake `handle_events`. Check
    that it can't hang: it quits on call 10 no matter what state the game is in.
- **security:** `save_high_score()` writes to disk. Check that:
  - it only ever writes `CONFIG_PATH`;
  - it never truncates or overwrites a file it couldn't parse (criterion 15b/c);
  - it keeps unknown keys;
  - it can't raise into the game loop at game over (criterion 15d).

  Tests must never touch the real `config.json`. The fixture redirects `CONFIG_PATH`, and
  15 builds its own `ScoreSystem` after monkeypatching. No new dependencies.
- **ux:** This is the first job where the player can lose.
  - Three enemy hits destroy a building, and defensive fire near the city is now safe.
    Check that this feels fair.
  - Known gaps, all deferred: SPACE on the game-over screen rebuilds the city but doesn't
    resume play (item 4); the score and high score stay at 0 in real play (item 5); some
    enemy missiles miss between buildings.
  - Flag it if a game over now arrives too fast or never arrives in a playtest.
- **ui:** Check frames 18–20. The gap left by a destroyed building should read as clearly
  gone. The game-over lines should be evenly spaced and not overlap. The colours are
  `COLOR_RED` / `COLOR_YELLOW` / `COLOR_YELLOW` / `COLOR_WHITE`.
