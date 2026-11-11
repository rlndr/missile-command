# 001-fix-shake-crash: Fix screen-shake crash on building hit and add pytest harness

## Problem
The game crashes the frame after an enemy missile hits a building. `check_collisions()` sets
`self.shake_intensity = 5`, the next `update(dt)` decays it to a float
(`max(0, self.shake_intensity - dt * 2)`, e.g. `4.9667`), and `draw()` then calls
`random.randint(-self.shake_intensity, self.shake_intensity)` with that float. On Python 3.12+
this raises `TypeError` (on older versions `ValueError`), which kills the game loop. The same
happens after an intercept (`shake_intensity = 8`). There are also no tests in the repo, so
nothing catches regressions like this.

## Scope
- Fix `MainGame.draw()` so screen-shake never passes a non-integer to `random.randint`. Move
  the offset calculation into a new method `MainGame.get_shake_offset()` that returns a tuple
  `(shake_x, shake_y)` of plain `int`s, each in the range `[-A, A]` where
  `A = math.ceil(self.shake_intensity)`, and `(0, 0)` when `shake_intensity <= 0`. `draw()`
  calls it in place of the two current `random.randint` lines.
- Replace the shake magic numbers with constants in `game/constants.py`:
  - `SCREEN_SHAKE_BUILDING_HIT = 5` (used in `check_collisions` for missile-hits-building)
  - `SCREEN_SHAKE_INTERCEPT = 8` (used in `check_collisions` for defence-hits-incoming)
  - `SCREEN_SHAKE_DECAY_RATE = 2.0` (intensity units lost per second, used in `update`)
  Values are unchanged, so the decay behaviour stays the same.
- Add the pytest harness:
  - `tests/__init__.py` is **not** required; `tests/conftest.py` must:
    - set `os.environ["SDL_VIDEODRIVER"] = "dummy"` and `os.environ["SDL_AUDIODRIVER"] = "dummy"`
      at module top, **before** anything imports `pygame`;
    - insert the repo root (parent of `tests/`) at the front of `sys.path`;
    - provide a `main_game` fixture that monkeypatches `systems.score.CONFIG_PATH` to a file
      under `tmp_path` **before** constructing `MainGame()` (ScoreSystem reads it in
      `__init__`), calls `start_game()`, sets `state = STATE_PLAYING`, sets
      `last_spawn_time` so `update()` never spawns a random missile during the test
      (e.g. `float("inf")`), yields the game, and on teardown drops the reference and calls
      `pygame.quit()`.
  - `tests/test_screen_shake.py` with the regression and unit tests listed below.
- Add a short "Running tests" section to `README.md` with the pytest command (with the SDL
  dummy env vars) and a note that `pytest` is a dev-only dependency.

## Out of scope
- Actually applying `shake_x`/`shake_y` to what is drawn. Today the offsets are computed and
  discarded; keep that behaviour (the fix is about not crashing). A later job can render the
  world through the offset.
- Explosions being driven by `pygame.time.get_ticks()` instead of `dt` (backlog item 2). Note:
  in a fast headless loop explosions go inactive on their first `update()`; tests must not
  assert that an explosion is still active after `update()`.
- Destroyed buildings staying in `self.buildings`, game-over detection, high-score saving
  (backlog item 3).
- Player explosions damaging buildings in `check_collisions` (backlog item 3).
- Removing `MainGame.__del__` (which calls `pygame.quit()`), requirements files, CI config.
- Broader collision/score unit tests (backlog "Later" item).

## Acceptance criteria
1. [test] **Regression, building hit:** with the `main_game` fixture and `random.seed(0)`,
   clear `incoming_missiles`, create one `IncomingMissile` targeted at `buildings[0]` and set
   its `position` to the centre of that building's rect
   (`building.position + (building.width / 2, building.height / 2)`). Run 10 frames of
   `update(DT_DEFAULT)` → `check_collisions()` → `draw()`. No exception is raised; after
   frame 1 the missile `is_destroyed` is `True`, and `shake_intensity` was equal to
   `SCREEN_SHAKE_BUILDING_HIT` immediately after the hitting `check_collisions()` call.
2. [test] The regression test in (1) proves it exercised the float path: after the `update()`
   of frame 2, `shake_intensity` is a non-integer float (`shake_intensity != int(shake_intensity)`)
   and the `draw()` that follows still succeeds. With the current `main` code this test fails
   with `TypeError` from `random.randint` (the builder confirms this in build.md).
3. [test] `draw()` succeeds when `shake_intensity` is set directly to `4.5`, `0.01`, and
   `SCREEN_SHAKE_INTERCEPT - 0.25`.
4. [test] `get_shake_offset()` with `shake_intensity = 4.97` and `random.seed(0)`, called
   200 times: every component satisfies `type(v) is int` and `-5 <= v <= 5`.
5. [test] `get_shake_offset()` returns exactly `(0, 0)` when `shake_intensity` is `0` and when
   it is `0.0`.
6. [test] **Decay:** after a building hit, running `update(DT_DEFAULT)` for 160 frames (more
   than `SCREEN_SHAKE_BUILDING_HIT / SCREEN_SHAKE_DECAY_RATE` = 2.5 s) leaves
   `shake_intensity == 0`, and a following `draw()` succeeds.
7. [test] An intercept (a `DefenseMissile` positioned inside a live `IncomingMissile`'s
   16×16 hit box, then `check_collisions()`) sets `shake_intensity == SCREEN_SHAKE_INTERCEPT`,
   and the next `update(DT_DEFAULT)` + `draw()` does not raise.
8. [test] **Harness isolation:** inside a test using `main_game`, `systems.score.CONFIG_PATH`
   resolves to a path under that test's `tmp_path`, and `os.environ["SDL_VIDEODRIVER"] == "dummy"`.
9. [test] The whole suite passes from the repo root with no display server, using
   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q`,
   and also passes when run as plain `python -m pytest -q` without the env vars set
   (conftest sets them). `git status` shows `config.json` unmodified after the run.
10. [visual] A frame rendered headless right after the building hit (fixture setup, hit,
    one more `update(DT_DEFAULT)`, `draw()`, `pygame.image.save`) looks the same as before
    the change: blue-gradient sky, launcher top-left in `COLOR_WHITE`, buildings in
    `COLOR_GRAY` along the bottom, and `SCORE: ...` in `COLOR_YELLOW` at top-right. No visual
    shake is expected (see Out of scope).

## Touch points
- `systems/game_loop.py`
  - `MainGame.draw()` — replace the two `random.randint(-self.shake_intensity, ...)` lines
    with a call to `get_shake_offset()`.
  - new `MainGame.get_shake_offset()` (docstring; uses `math.ceil`; add `import math`).
  - `MainGame.check_collisions()` — `5` → `SCREEN_SHAKE_BUILDING_HIT`, `8` → `SCREEN_SHAKE_INTERCEPT`.
  - `MainGame.update()` — `dt * 2` → `dt * SCREEN_SHAKE_DECAY_RATE`.
- `game/constants.py` — new section "Screen shake" with `SCREEN_SHAKE_BUILDING_HIT`,
  `SCREEN_SHAKE_INTERCEPT`, `SCREEN_SHAKE_DECAY_RATE`.
- `tests/conftest.py` (new), `tests/test_screen_shake.py` (new).
- `README.md` — "Running tests" section.

Expected diff: ~20 lines in game code, ~150 lines of tests.

## Notes for reviewers
- **security:** tests must never write the real `REPO/config.json`. Check the fixture
  monkeypatches `systems.score.CONFIG_PATH` *before* `MainGame()` is constructed, and that no
  test path reaches `save_high_score()` against the real file. No new runtime dependencies;
  `pytest` is dev-only.
- **code:** `shake_x`/`shake_y` are still unused after `get_shake_offset()` is called — this
  is pre-existing and intentionally left (out of scope), not dead code introduced by this job.
  Check the fix truncates/ceils rather than just wrapping `int()` around the result of
  `randint` (the crash is in the *arguments*). Check `conftest.py` sets the SDL env vars before
  any `pygame` import (including transitive imports via `systems.game_loop`). `MainGame.__del__`
  calls `pygame.quit()`; check the fixture teardown doesn't leave a stale `MainGame` that could
  be garbage-collected in the middle of a later test and quit pygame under it. Tests should
  pin `random.seed(...)` and avoid depending on wall-clock time (`last_spawn_time` set so no
  spawns, no assertions on explosion activity after `update()`).
- **ux:** player-facing change is "the game no longer crashes the moment a building is hit".
  Screen shake is still not visible — that's expected for this slice.
- **ui:** no visual change intended; confirm the rendered frame in criterion 10 matches the
  existing look and the HUD score is still drawn top-right.
