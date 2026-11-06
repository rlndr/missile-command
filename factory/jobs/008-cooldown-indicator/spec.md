# 008-cooldown-indicator: Reload bar under the launcher

## Problem
After a shot the launcher reloads for `BASE_COOLDOWN_TIME` (1.5 s). Clicks during that time do
nothing, and nothing on screen says so. The player can't tell an ignored click from a missed
one, or know when the next shot is ready. GAME_DESIGN.md §4.2 asks for a "visual indicator when
on cooldown/offline", and `DefensiveBase.update()` already keeps a `cooldown_ratio` "for the
visual indicator", but nothing draws it.

## Scope
- **`DefensiveBase.reload_progress()`** (new, `entities/base.py`). Returns a float in
  `[0.0, 1.0]`: `1 - cooldown_time / BASE_COOLDOWN_TIME`, clamped to that range. It is worked out
  from `cooldown_time` each time it is called. It does **not** read `cooldown_ratio`, which is
  not set in `__init__` and goes stale after `start_cooldown()` until the next `update()`.
  It returns `0.0` when `is_active` is False, so the bar never looks ready while
  `can_fire()` is False.
- **`DefensiveBase.cooldown_bar_rects()`** (new). Returns `(track_rect, fill_rect)` as
  `pygame.Rect`s:
  - track: `left = get_bounds().left`, `top = get_bounds().bottom + COOLDOWN_BAR_GAP`,
    `width = self.width`, `height = COOLDOWN_BAR_HEIGHT`. With the current numbers that is
    `Rect(5, 34, 60, 4)`.
  - fill: same left, top and height as the track. `width = int(track.width * reload_progress())`,
    rounded down so the bar is only full when the reload is done.
- **`DefensiveBase.draw_base()`** also draws the bar after the launcher body and tube:
  - The whole track in `COOLDOWN_BAR_TRACK_COLOR`.
  - Then the fill on top: `COOLDOWN_BAR_READY_COLOR` when `can_fire()` is True,
    `COOLDOWN_BAR_FILL_COLOR` otherwise. When the fill width is 0, nothing is drawn over the track.
  - The signature and defaults of `draw_base()` do not change. `MainGame.draw()` already calls
    it, so `systems/game_loop.py` needs no change.
- **New constants** in `game/constants.py` under "Defensive base settings" (see Touch points).
- **README.** One sentence in "Gameplay" saying that the bar under the launcher fills while it
  reloads and turns yellow when it can fire.
- **Tests.** Add a new file, `tests/test_cooldown_indicator.py`. Do not edit existing test files.

## Out of scope
- Changing `BASE_COOLDOWN_TIME`, how the cooldown counts down, or any firing rule.
- Removing or renaming `cooldown_ratio`, or setting it in `__init__`. `tests/test_reset_cooldown.py`
  still checks it after `reset()`.
- A separate "offline" look for the launcher. Nothing sets `is_active = False` today. The bar
  only has to show an empty track in that case.
- Drawing the bar on the start, pause or game-over screens. Those screens don't draw the
  launcher, and this job doesn't change that.
- Applying screen shake to the launcher or bar. `draw()` works out a shake offset but never
  applies it. That is a separate bug.
- Sound or a flash when the launcher becomes ready.
- GAME_DESIGN.md edits.

## Acceptance criteria
Tests patch `systems.score.CONFIG_PATH` to a file under `tmp_path` before building any
`MainGame` (the `main_game` fixture already does this). Other terms:
- `FIRE` means `{"fire_missile": (400, 300)}`.
- A **start-screen game** is a `MainGame()` built with that patch and left in `STATE_START`.
- A **bare base** is a `DefensiveBase()` built directly, with no game.
- **Surface draw** means: make a `pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))`, fill it with
  `COLOR_BLACK`, call `base.draw_base(surface)`, then read pixels with
  `surface.get_at((x, y))[:3]`.
- With current constants, `TRACK = Rect(5, 34, 60, 4)` and the sample row is `y = 35`.

1. [test] **Constants.** `COOLDOWN_BAR_HEIGHT == 4` and `COOLDOWN_BAR_GAP == 4`, both ints.
   `COOLDOWN_BAR_TRACK_COLOR`, `COOLDOWN_BAR_FILL_COLOR` and `COOLDOWN_BAR_READY_COLOR` are
   3-tuples of ints in 0–255 and are all different from each other. They equal
   `COLOR_DARK_BLUE`, `COLOR_ORANGE` and `COLOR_YELLOW` respectively.
2. [test] **Bar position.** On a bare base, `cooldown_bar_rects()[0] == pygame.Rect(5, 34, 60, 4)`.
   It does not `colliderect` `base.get_bounds()`. It lies inside
   `pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)`. Its `left` and `width` equal those of
   `get_bounds()`. The fill rect has the same `left`, `top` and `height` as the track.
3. [test] **`reload_progress()` values on a bare base.**
   - Freshly built (`cooldown_time == BASE_COOLDOWN_TIME`): `0.0`.
   - After `reset()`: `1.0`.
   - After `reset()` then `start_cooldown()`, with no `update()`: `0.0`.
   - Then `update(0.375)`: `pytest.approx(0.25)`. Then `update(0.375)` again:
     `pytest.approx(0.5)`.
   - With `is_active = False` and `cooldown_time = 0.0`: `0.0`.
4. [test] **Clamped, and full only when ready.** Parametrise `cooldown_time` over
   `-1.0, 0.0, 0.001, 0.75, BASE_COOLDOWN_TIME, BASE_COOLDOWN_TIME * 2`. For each,
   `0.0 <= reload_progress() <= 1.0`, and `(reload_progress() == 1.0) == base.can_fire()`.
   Also `(fill.width == track.width) == base.can_fire()`. So at `0.001` the fill is 59 px,
   not 60.
5. [test] **Fill widths.** On a bare base: after `reset()`, fill width is `60`. After
   `start_cooldown()`, `0`. After `update(0.375)`, `15`. After another `update(0.375)`, `30`.
   After `update(BASE_COOLDOWN_TIME)`, `60`.
6. [test] **Pixels: ready.** Bare base, `reset()`, surface draw. The pixels at
   `x = 5, 34, 64` on row 35 are `COOLDOWN_BAR_READY_COLOR`. The pixels at `(4, 35)` and
   `(65, 35)` are `COLOR_BLACK` (the bar doesn't spill out). The pixel at `(30, 32)` in the gap
   is `COLOR_BLACK`. The launcher body pixel at `(30, 15)` is still `COLOR_WHITE`.
7. [test] **Pixels: just fired.** Bare base, `reset()`, `start_cooldown()`, surface draw. Every
   pixel in `TRACK` is `COOLDOWN_BAR_TRACK_COLOR`. None is `COOLDOWN_BAR_FILL_COLOR` or
   `COOLDOWN_BAR_READY_COLOR`.
8. [test] **Pixels: half reloaded.** Bare base, `reset()`, `start_cooldown()`, `update(0.75)`,
   surface draw. Pixels at `x = 5, 20, 34` on row 35 are `COOLDOWN_BAR_FILL_COLOR`. Pixels at
   `x = 35, 50, 64` are `COOLDOWN_BAR_TRACK_COLOR`. No pixel in `TRACK` is
   `COOLDOWN_BAR_READY_COLOR`.
9. [test] **Fills over a real reload.** Using the `main_game` fixture, `handle_actions(FIRE)`
   then call `update(DT_DEFAULT)` and `check_collisions()` 100 times. After every frame:
   - the fill width is greater than or equal to the previous frame's;
   - `(fill.width == 60) == game.base.can_fire()`.
   The width is below 60 after frame 89 and equals 60 after frame 91. Check 89 and 91, not 90:
   `90 * DT_DEFAULT` sits right on 1.5 s and float drift makes that frame unreliable.
10. [test] **Wired into the game frame.** Using `main_game`: `handle_actions(FIRE)`,
    `update(0.75)`, `draw()`. On `game.screen`, `(10, 35)` is `COOLDOWN_BAR_FILL_COLOR` and
    `(50, 35)` is `COOLDOWN_BAR_TRACK_COLOR`. Then `update(1.0)` and `draw()`: `(10, 35)` and
    `(50, 35)` are both `COOLDOWN_BAR_READY_COLOR`.
11. [test] **Pause freezes the bar.** Using `main_game`: `handle_actions(FIRE)`, `update(0.75)`.
    The fill width is `30`. `handle_actions({"toggle_pause": True})` twice (pause, then resume)
    gives `state == STATE_PLAYING`. The fill width is still `30` and `can_fire()` is False.
12. [test] **New game shows a full bar.** On a start-screen game: `handle_actions({"start": True})`,
    `handle_actions(FIRE)`, `update(0.3)`. Mark every building destroyed, then call
    `check_collisions()` and `check_game_over()`, giving `STATE_GAME_OVER` with fill width below
    60. `handle_actions({"start": True})` gives fill width `60`. After `draw()`, the pixel at
    `(10, 35)` is `COOLDOWN_BAR_READY_COLOR`.
13. [test] **Not on menu screens.** On a start-screen game, `draw_start_screen()` leaves
    `(10, 35)` with none of the three bar colours. The same holds after setting
    `state = STATE_PAUSED` and calling `draw_start_screen()` again.
14. [test] All existing tests pass unchanged. The full suite passes with the README command,
    and the real `config.json` is byte-for-byte unchanged.
15. [visual] **Mid-reload frame.** Using `main_game`: `FIRE`, then 45 frames of
    `update(DT_DEFAULT)` + `check_collisions()`, then `draw()`. Under the white launcher in the
    top-left there is a thin bar the launcher's width, with a small gap above it. The left half
    is `COLOR_ORANGE` and the right half `COLOR_DARK_BLUE`. It stands out clearly against the
    blue sky. The yellow defense missile is in flight. The HUD score is unchanged at top right.
16. [visual] **Ready frame.** The same game after 60 more frames, then `draw()`. The whole bar
    is `COLOR_YELLOW`, the same yellow as defense missiles. Nothing else near the launcher has
    changed.

## Touch points
- `entities/base.py`:
  - new `DefensiveBase.reload_progress()`;
  - new `DefensiveBase.cooldown_bar_rects()`;
  - `DefensiveBase.draw_base()` draws the track and the fill.
- `game/constants.py`, under "Defensive base settings":
  - `COOLDOWN_BAR_HEIGHT = 4`: bar height in px.
  - `COOLDOWN_BAR_GAP = 4`: px between the launcher's bottom edge and the bar.
  - `COOLDOWN_BAR_TRACK_COLOR = COLOR_DARK_BLUE`: empty part of the bar.
  - `COOLDOWN_BAR_FILL_COLOR = COLOR_ORANGE`: filled part while reloading.
  - `COOLDOWN_BAR_READY_COLOR = COLOR_YELLOW`: the full bar when `can_fire()` is True.
  These must be defined after the `COLOR_*` names they reference.
- `README.md`: one sentence in "Gameplay".
- `tests/test_cooldown_indicator.py` (new).
- `systems/game_loop.py`: no change expected.

Expected diff: about 30 lines of game code and constants, and 150–200 lines of tests.
Parametrise criterion 4. Share a surface-draw helper and a pixel-region helper like `_region`
in `tests/test_scoring.py`.

## Notes for reviewers
- **code:**
  - `reload_progress()` must work from `cooldown_time` (and `is_active`), not `cooldown_ratio`.
    A bare `DefensiveBase()` has no `cooldown_ratio` until `update()` runs, and right after
    `start_cooldown()` the ratio is out of date.
  - Fill width is rounded down with `int()`. Don't use `round()`, which would show a full bar
    for the last ~12 ms of the reload while `can_fire()` is still False.
  - Bar geometry comes from `get_bounds()` and `self.width`, not repeated literals. The only
    new numbers are the constants above.
  - `draw_base()` keeps its current parameters. Don't add a game reference to the base.
- **security:** No new file, network or config I/O. Tests must patch `CONFIG_PATH` before
  building a `MainGame`. Surface-draw tests need no `MainGame` at all.
- **ux:**
  - The player can now see the reload. Yellow means "you can fire", matching the colour of
    their own missiles. Orange means reloading.
  - The bar is only full and yellow when a click will fire (criterion 4). Any frame where it
    looks ready but a click is ignored is a bug.
  - Pausing doesn't move the bar, and a new game always starts with it full (from 007).
- **ui:**
  - Check frames 15 and 16. The bar should be clearly separate from the launcher body (4 px
    gap), the same width as the launcher, and readable against the top of the sky gradient.
  - It must not overlap the HUD score at top right or the missile tube.
  - The bar is drawn before buildings, missiles and explosions, so an explosion right at the
    launcher can cover it. That is acceptable.
