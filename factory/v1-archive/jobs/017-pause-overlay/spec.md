# 017-pause-overlay: Pause shows the frozen battlefield, dimmed, with the keys that work while paused

## Problem
Pressing ESC during play swaps the whole battlefield for a flat dark-blue menu
(`draw_start_screen()` fills `COLOR_DARK_BLUE` in `STATE_PAUSED` as well as on the start
screen). While paused the player can't see the missiles, explosions or city they will go back
to. The pause screen also lists the start-screen controls, and two of them do nothing while
paused: "Mouse Click: Launch defense missile" and "SPACE: Start / Restart". The player wants
pausing to dim the frozen game and list the controls that actually work there.

## Scope
- **Scene drawing without flip** (`systems/game_loop.py`, `MainGame`):
  - New method `draw_scene()` holds everything `draw()` does today, in the same order (sky
    gradient, ground, tower, buildings, trails, missiles, explosions, `draw_hud()`), but
    does **not** call `pygame.display.flip()`.
  - `draw()` becomes `self.draw_scene()` followed by `pygame.display.flip()`. Play frames
    look exactly the same as now.
  - `draw_scene()` only reads state. It must not move, add or remove anything, or change
    timers, trails, cooldowns, score or `shake_intensity`. (The existing unused
    `get_shake_offset()` call can stay as it is.)
- **Dim overlay**:
  - New method `draw_pause_overlay()` blits one full-screen `pygame.SRCALPHA` surface filled
    with `(*PAUSE_OVERLAY_COLOR, PAUSE_OVERLAY_ALPHA)` at `(0, 0)` onto `self.screen`. It
    doesn't flip. The surface may be built once in `__init__` and reused.
  - `draw_start_screen()` in `STATE_PAUSED`: call `draw_scene()`, then
    `draw_pause_overlay()`, then draw the `menu_lines()` text exactly as now (centred at
    `SCREEN_WIDTH // 2`, one font per size), then flip **once**. Text goes on top of the
    overlay, so it is at full brightness.
  - `STATE_START` and `STATE_GAME_OVER` keep their current drawing (flat `COLOR_DARK_BLUE`
    fill plus the existing 128-alpha black overlay, no scene). Only the pause branch changes.
- **Pause text** (`menu_lines()` when `state == STATE_PAUSED`). It returns exactly these
  lines, top to bottom (`mid = SCREEN_HEIGHT // 2`):

  | text | size | colour | centre_y |
  |------|------|--------|----------|
  | `"PAUSED"` | 48 | `COLOR_WHITE` | `mid - 120` |
  | `f"Score: {score:,}"` | 36 | `COLOR_YELLOW` | `mid - 30` |
  | `"Controls:"` | 36 | `COLOR_WHITE` | `mid + 80` |
  | `"ESC: Resume"` | 36 | `COLOR_WHITE` | `mid + 110` |
  | `"M: Mute sound"` / `"M: Unmute sound"` (from `self.sound.muted`, as now) | 36 | `COLOR_WHITE` | `mid + 140` |
  | `"Press ESC to Resume"` | 48 | `COLOR_YELLOW` | `mid + 190` |

  - The pause screen no longer shows `"Mouse Click: Launch defense missile"`,
    `"SPACE: Start / Restart"` or `"ESC: Pause / Resume"`.
  - Job 012's mute line keeps its exact tuple and position (`36, COLOR_WHITE, mid + 140`),
    because `tests/test_sound.py::test_menu_mute_line` asserts it for the pause screen.
  - **Start screen text is unchanged**: same header, same five control lines (including
    `"SPACE: Start / Restart"` and `"Mouse Click: Launch defense missile"`), same prompt, same
    positions. Restructure `menu_lines()` however is clearest, as long as the start list
    stays identical.
- **Constants** (`game/constants.py`): a new `# Pause overlay` block after the `# Game states`
  block:
  - `PAUSE_OVERLAY_COLOR = COLOR_BLACK`: colour of the dimming layer.
  - `PAUSE_OVERLAY_ALPHA = 160`: overlay opacity, 0–255. Scene colours end up at about 37 %
    brightness.
- **README**: add one short new paragraph at the **end** of the "Gameplay" section (after
  "…Press SPACE to restart."), for example: "Press ESC during play to pause. The battlefield
  freezes and dims, and the pause screen lists the keys that work there: ESC to resume and M
  to mute or unmute." Don't edit the Features list (job 016 adds a bullet there) or the long
  Gameplay line. The Controls table is already correct and stays as it is.
- **Tests**: new file `tests/test_pause_overlay.py`. No existing test is edited.

### Does this cover the next backlog item?
Yes. The next item is "Pause screen text: replace 'SPACE: Start / Restart' … with the keys
that work there, ESC to resume". This job removes the SPACE line (and the dead mouse line)
from the pause screen and lists only ESC (resume) and M (mute/unmute), the only keys
`handle_actions()` acts on in `STATE_PAUSED`. Once this job merges, that item has nothing
left to do and the orchestrator can close it as covered by 017. The builder does **not**
edit `factory/backlog.md`.

## Out of scope
- Any change to input handling or state transitions. `InputSystem.handle_events()` and
  `handle_actions()` don't change, and SPACE and mouse clicks still do nothing while paused.
- A clickable "Resume" button, a "quit to menu" key, or listing "close window to quit" (the
  window close button isn't a key binding).
- Changing the start screen or game over screen look or text.
- Blur, fade-in animation, or a pause sound.
- Applying or fixing the unused screen-shake offset in `draw()`.
- Editing GAME_DESIGN.md (its PAUSED → RESUMING "click Resume" state machine is aspirational).
- Editing the stale docstring of `tests/test_bottom_launcher.py::test_not_on_menu_screens`
  ("The start and pause screens draw neither ground nor tower"). Its assertions still pass,
  because dimmed ground and tower colours differ from `COLOR_GROUND` and `COLOR_WHITE`.

## Acceptance criteria
Terms:
- `main_game` is the conftest fixture (started, `STATE_PLAYING`, `CONFIG_PATH` patched, no
  random spawns). `mid = SCREEN_HEIGHT // 2`.
- **Parked missile** means an `IncomingMissile(Vector2(100, 500))` with
  `position = Vector2(100, 200)` and `velocity = Vector2(0, 0)`, appended to
  `incoming_missiles` (the `_park` pattern from `tests/test_sound.py`).
- **Dimmed(c)** for an RGB colour `c` means each channel is within ±2 of
  `round(ch * (255 - PAUSE_OVERLAY_ALPHA) / 255)`.
- **Sample points** are sky `(20, 20)`, ground `(5, 590)`, tower body `(400, 555)` and the
  parked missile `(100, 200)`. No pause text covers any of them.

1. [test] **Constants.** `PAUSE_OVERLAY_COLOR == COLOR_BLACK` and `PAUSE_OVERLAY_ALPHA == 160`.
2. [test] **Pause dims the live scene.** On `main_game` with a parked missile, call `draw()`
   and record the RGB at each sample point. Then `handle_actions({"toggle_pause": True})`
   (`state == STATE_PAUSED`) and `draw_start_screen()`. Each sample point's paused RGB is
   Dimmed(its play RGB), and the paused missile pixel is Dimmed(`COLOR_RED`). The paused
   pixels at the ground, tower and missile all differ from the paused sky pixel, so the
   scene really is drawn under the overlay and is not a flat fill.
3. [test] **Text sits on top of the overlay.** On the paused frame from criterion 2, the
   region `Rect(300, mid - 140, 200, 40)` ("PAUSED") contains at least one pixel exactly
   `COLOR_WHITE`. The region `Rect(250, mid + 125, 300, 30)` (mute line) contains at least
   one exactly `COLOR_WHITE` pixel. The region `Rect(200, mid + 170, 400, 40)` (prompt)
   contains at least one exactly `COLOR_YELLOW` pixel. (No dimmed scene pixel can reach
   these values, because the brightest dimmed channel is about 95.)
4. [test] **Exact pause lines.** In `STATE_PAUSED` with `score_system.score = 1234`,
   `menu_lines()` equals the six-row table in Scope with `"Score: 1,234"` and
   `"M: Mute sound"`. After `sound.toggle_mute()`, it is the same list with
   `"M: Unmute sound"` in the fifth row.
5. [test] **No dead controls on the pause screen.** In `STATE_PAUSED`, no
   `menu_lines()` text contains `"SPACE"`, `"Mouse"`, `"Click"` or `"Start"`
   (case-insensitive), and the texts include `"ESC: Resume"`. The start screen's
   `menu_lines()` is unchanged: it still includes `"SPACE: Start / Restart"`,
   `"Mouse Click: Launch defense missile"`, `"ESC: Pause / Resume"` and
   `"Press SPACE to Start"`, at `mid + 80`, `mid + 50`, `mid + 110` and `mid + 190`.
6. [test] **The listed keys work while paused, end to end.** On `main_game`, pause with
   `handle_actions({"toggle_pause": True})`. Post `KEYDOWN K_m` with `pygame.event.post`,
   then `handle_actions(input_system.handle_events())`: `sound.muted is True`,
   `state == STATE_PAUSED`, and the pause `menu_lines()` now shows `"M: Unmute sound"`. Post
   `KEYDOWN K_ESCAPE` and do the same: `state == STATE_PLAYING`. (Call
   `pygame.event.clear()` before each post.)
7. [test] **Pausing and drawing change nothing.** On `main_game` with a parked missile, a
   player explosion from `explosion_pool.get_explosion(300, 300, is_player=True)` appended
   to `explosions`, `score_system.score = 77`, `game_time = 12.5`, and
   `base.cooldown_time = 0.7`: pause, call `draw_start_screen()` 10 times, then resume. The
   game time, score, missile position and trail, explosion radius and `is_active`,
   cooldown, building count and `shake_intensity` all equal their values before the pause.
8. [test] **One flip per frame.** With `pygame.display.flip` monkeypatched to a counter:
   `draw_scene()` makes 0 calls, `draw()` makes exactly 1, and `draw_start_screen()` makes
   exactly 1 in each of `STATE_PAUSED`, `STATE_START` and `STATE_GAME_OVER`.
9. [test] **Start and game over screens don't show the scene.** On `main_game` with a parked
   missile, set `state = STATE_START`, call `draw_start_screen()`, and the pixel at
   `(100, 200)` equals the pixel at `(20, 20)` (a uniform background). Do the same with
   `state = STATE_GAME_OVER`.
10. [test] **Pause through the real loop.** Use the fake-clock loop pattern from
    `tests/test_game_states.py::test_pause_does_not_advance_game_time` (copy the helper; do
    not import it). The script is 5 empty frames, `{"toggle_pause": True}`, 5 empty frames,
    then `{"quit": True}`. Spy on `draw_scene` (wrap, don't replace) and `draw_start_screen`.
    `draw_start_screen` is called 6 times, `draw_scene` 11 times (5 play frames plus 6 pause
    frames), and `state == STATE_PAUSED` at the end.
11. [test] All existing tests pass unedited, in particular `tests/test_game_states.py::test_menu_text`,
    `tests/test_sound.py::test_menu_mute_line`, and the `test_not_on_menu_screens` tests in
    `tests/test_bottom_launcher.py` and `tests/test_cooldown_indicator.py`. The suite passes
    with the README command, and the real `config.json` is byte-for-byte unchanged.
12. [visual] **Paused mid-fight.** On `main_game`, `random.seed(0)`, fire one defense missile
    at `(400, 300)`, set `last_spawn_time = 0.0`, run `update(DT_DEFAULT)` and
    `check_collisions()` 300 times, then pause and render `draw_start_screen()`. The frozen
    sky, city, tower, reload bar, enemy missiles with trails and the HUD are all visible but
    clearly darkened. Over them, centred, "PAUSED" (white, large), "Score: N" (yellow),
    "Controls:", "ESC: Resume", "M: Mute sound" (white), and "Press ESC to Resume" (yellow,
    large) are crisp and easy to read. No SPACE or mouse line is shown.
13. [visual] **Paused during rapid fire, muted.** Same as 12, but with `game_time = 64.0`
    before the updates (so the tower is red, `LAUNCHER_RAPID_FIRE_COLOR`) and
    `sound.toggle_mute()` before rendering. The dimmed tower is still recognisably red, and
    the mute line reads "M: Unmute sound" in the same position.

## Touch points
- `game/constants.py`: new `# Pause overlay` block after `# Game states` with
  `PAUSE_OVERLAY_COLOR = COLOR_BLACK` and `PAUSE_OVERLAY_ALPHA = 160`, each with a comment.
- `systems/game_loop.py` (`MainGame`):
  - new `draw_scene()` (the body of `draw()` minus the flip); `draw()` calls it and then flips;
  - new `draw_pause_overlay()` (optionally a cached overlay surface built in `__init__`);
  - `draw_start_screen()`: the `STATE_PAUSED` path draws scene, then overlay, then text,
    then one flip; the start and game over paths are unchanged;
  - `menu_lines()`: the pause branch returns its own control list (see the Scope table);
    the start branch output is unchanged.
  - Don't touch `update()`, `rapid_fire_active()`, `spawn_incoming_missile()` or the spawn
    code (job 016 is editing those in parallel).
- `README.md`: one new paragraph at the end of the Gameplay section.
- `tests/test_pause_overlay.py` (new).

Expected diff: about 30–40 lines in `game_loop.py`, 3 in constants, 2 in README, and
180–230 lines of tests.

## Notes for reviewers
- **code:**
  - `draw()` must still produce pixel-identical play frames. The refactor is a move of its
    body into `draw_scene()`, not a rewrite. Check that nothing between the gradient and
    `draw_hud()` was reordered.
  - Exactly one `flip()` per loop iteration in every state (criterion 8). A flip inside
    `draw_scene()` would show an undimmed frame for one refresh and cause visible flicker.
  - `draw_scene()` must be read-only (criterion 7), because it now also runs every paused
    frame. In particular, nothing in it may call `update()`, touch trails, or advance
    `self.timer`. Resuming already calls `timer.reset()`, so the paused frames don't
    cause a time jump.
  - Merge safety with **016-rapid-fire-double-spawn**: 016 changes only `update()`'s
    interval lines, adds `current_spawn_interval()` after `spawn_incoming_missile()`, adds a
    constant under `# Difficulty settings`, and adds a README Features bullet. This job
    stays out of all four places. Its constants go after `# Game states` and its README
    change goes at the end of Gameplay.
  - Keep the mute tuple `("M: …", 36, COLOR_WHITE, mid + 140)` exact. Moving it breaks job
    012's test.
- **security:** No new file, network or config I/O. Tests patch `CONFIG_PATH` through
  `main_game`, scope their `pygame.display.flip` / `utils.timer.time` monkeypatches to the
  test, and clear the event queue around posted key events.
- **ux:**
  - "ESC: Resume" in the list and the "Press ESC to Resume" prompt say the same thing. The
    prompt is kept because `test_menu_text` requires it, and the list is meant to be
    complete. Judge whether the repetition reads as clear or as clutter.
  - Check that the dim level (`PAUSE_OVERLAY_ALPHA = 160`) makes it obvious the game is
    paused, while threats stay visible enough for the player to plan before resuming.
  - SPACE and clicks still do nothing while paused, and now the screen no longer suggests
    they do.
- **ui:** Check frames 12 and 13.
  - The text should be crisp white/yellow over the darkened scene, not dimmed itself.
  - The gap between "Score:" (`mid - 30`) and "Controls:" (`mid + 80`) is wider than
    before because the list is shorter and the mute line is fixed at `mid + 140`. Check
    that the block still looks balanced.
  - The dimmed HUD score at the top right and the "Score:" line both appear. Check that this
    doesn't look like a mistake.
