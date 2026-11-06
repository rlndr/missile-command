# 015-repeat-rapid-fire: Rapid-fire window repeats every minute of play

## Problem
Job 013 added one rapid-fire window: at 60 s of `game_time` the launcher turns red for
10 s, reloads in 0.1 s and plays the `"laser"` sound. After 70 s it never comes back, so
players who hold out longer get nothing more. The player wants the same 10-second window
to come back every 60 seconds for the whole game.

**Interpretation used in this spec:** a window opens at every whole minute of
`game_time` after the first and lasts `RAPID_FIRE_DURATION` (10 s). So the windows are
[60, 70), [120, 130), [180, 190), ... and they keep going for as long as the game runs.
There is **no** window at [0, 10). Each window is 10 s on, then 50 s off. As in 013, only
`game_time` counts. It only goes up while `STATE_PLAYING`, so pauses and menus never move
a window, and `start_game()` sets it back to 0 so a new game's first window is at 60 s.

## Scope
- **Repeating window** (`systems/game_loop.py`, `MainGame.rapid_fire_active()`):
  - It returns `True` exactly when `game_time >= RAPID_FIRE_START_TIME` and
    `(game_time - RAPID_FIRE_START_TIME) % RAPID_FIRE_INTERVAL < RAPID_FIRE_DURATION`.
    It is still the only place that decides whether a window is open.
  - Update the docstring. It currently says "once-per-game".
  - `update()` still makes one `self.base.set_rapid_fire(self.rapid_fire_active())` call
    each frame. No new timer, counter or attribute on `MainGame`.
- **Launcher** (`entities/base.py`): no change expected. `set_rapid_fire()` already treats
  every off-to-on switch the same way, so each new window cuts a running 1.5 s reload down
  to `RAPID_FIRE_COOLDOWN_TIME`, and each window end lets the short reload finish. The
  same goes for the red tower colour and the `"laser"` / `"launch"` sound choice in
  `spawn_defense_missile()`. These already follow `base.rapid_fire`.
- **Constants** (`game/constants.py`): add `RAPID_FIRE_INTERVAL = 60.0` (seconds from one
  window opening to the next) in the rapid-fire block. Change that block's heading comment
  from "once per game, after a minute of play" to say the window repeats every minute.
  The other values stay the same.
- **README**: in "Gameplay", rewrite the 013 sentence so it says that every 60 seconds of
  play (at 1:00, 2:00, 3:00, ...) the launcher turns red for 10 seconds and can fire every
  0.1 s, with a laser sound on each shot. Change nothing else.
- **Tests**: add a new file, `tests/test_repeat_rapid_fire.py`, for the criteria below.

### Existing tests: what changes
I checked every test in `tests/test_rapid_fire.py`. None of them say the window happens
only once. The latest `game_time` any of them reach is about 70.3 s
(`test_normal_reload_after_window`, `test_game_frame_tower_red_in_window`), well before
the second window at 120 s. The `[0.0, 59.99, 70.0]` → `False` and
`[60.0, 65.0, 69.99]` → `True` cases in `test_window_boundaries` are still right with the
new rule. **So no existing test should need editing.** If any of the tests below fail,
treat it as a bug in the build, not as a reason to change the test.
- The ones most likely to be affected: `test_window_boundaries`,
  `test_launcher_follows_window`, `test_normal_reload_after_window`,
  `test_window_end_mid_reload_finishes_short_reload`, `test_new_game_clears_window`,
  `test_game_frame_tower_red_in_window`, and `test_constants`. `test_constants` only checks
  the four 013 constants, which don't change.
- `tests/test_wave_counter.py` sets `game_time` to 65, 95 and 30000. At 65 and 30000 the
  window is now open (and at 30000 it wasn't before), but those tests only check the wave
  text, layout and HUD pixels, never the launcher. They must pass unedited.
- `tests/test_sound.py`, `tests/test_cooldown_indicator.py` and
  `tests/test_reset_cooldown.py` must pass unedited.

## Out of scope
- Making the interval, duration or first start time configurable at runtime, or saving
  anything to `config.json`.
- A window at 0–10 s. Windows that get longer, shorter or more frequent with wave number.
- Any link between windows and waves. A window opens at the start of every other wave
  (wave 3, 5, 7, ...) only because 60 is a multiple of `WAVE_DURATION`. Nothing in the code
  should rely on that.
- A HUD countdown to the next window, an "ending soon" warning, flashing, a screen tint,
  or a sound when a window opens or closes.
- Hold-to-fire auto-fire, other power-up types, random pickups.
- Changes to `entities/base.py`, `systems/sound.py`, scoring, spawning, menu text, or
  GAME_DESIGN.md.

## Acceptance criteria
Terms (same as 013):
- `FIRE = {"fire_missile": (400, 300)}`.
- A **spy** is `calls = []` plus `monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)`.
- `main_game` is the conftest fixture: playing, `CONFIG_PATH` patched, no random spawns.
- **Bring to t** means `game.game_time = t - 0.1` and then `game.update(0.1)`.
- **Launches** means the change in `len(game.defense_missiles)` across one
  `handle_actions()` call, or a count of spy calls.

1. [test] **Constants.** `RAPID_FIRE_INTERVAL == 60.0`.
   `RAPID_FIRE_START_TIME == 60.0`, `RAPID_FIRE_DURATION == 10.0` and
   `RAPID_FIRE_COOLDOWN_TIME == 0.1` are unchanged.
   `0 < RAPID_FIRE_DURATION < RAPID_FIRE_INTERVAL`.
2. [test] **Window boundaries across several minutes.** On `main_game`, set `game_time`
   directly and call `rapid_fire_active()`:
   - `True` for `60.0, 69.99, 120.0, 125.0, 129.99, 180.0, 189.99, 3600.0, 3605.0`;
   - `False` for `0.0, 5.0, 9.99, 59.99, 70.0, 100.0, 119.99, 130.0, 179.99, 190.0, 3610.0`.
3. [test] **Exactly one on/off pair per minute.** On `main_game` after `start_game()`, call
   `update(0.1)` 2000 times, which takes `game_time` from 0 to about 200 s. Then:
   - after every call, `game.base.rapid_fire == game.rapid_fire_active()`;
   - `base.rapid_fire` goes from `False` to `True` exactly 3 times, and the `game_time` at
     each switch is within 0.11 s after 60, 120 and 180;
   - it goes from `True` to `False` exactly 3 times, within 0.11 s after 70, 130 and 190;
   - the number of calls that leave `base.rapid_fire` `True` is between 297 and 303
     (3 windows × 10 s ÷ 0.1 s, give or take one step at each edge).
4. [test] **Fast reload in the second and third windows.** On `main_game`, bring to 120.1
   and set `base.cooldown_time = 0.0`. Then:
   - `handle_actions(FIRE)` launches 1 missile and
     `base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)`;
   - after `update(0.05)` a click launches nothing;
   - repeating `update(0.11)` then `handle_actions(FIRE)` 20 times gives 20 launches, and
     `rapid_fire_active()` is still `True` at the end.

   Doing the same from 180.1 also gives 20 launches.
5. [test] **Normal reload between windows.** On `main_game`, bring to 100.0 and set
   `base.cooldown_time = 0.0`. A click launches 1 missile and sets
   `base.cooldown_time == BASE_COOLDOWN_TIME`, and a second click after `update(0.2)`
   launches nothing. The same is true at 150.0.
6. [test] **A new window cuts a running slow reload.** On `main_game`:
   - Bring to 119.9, set `base.cooldown_time = 0.0`, and click. 1 launch, and
     `cooldown_time == BASE_COOLDOWN_TIME`.
   - `update(0.2)` (crosses 120). Now `base.rapid_fire is True` and
     `base.cooldown_time <= RAPID_FIRE_COOLDOWN_TIME`.
   - After a further `update(0.11)`, `base.can_fire() is True`, and a click gives 1 launch
     with `cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)`.
7. [test] **The short reload finishes after the second window ends.** On `main_game`,
   bring to 129.95, set `base.cooldown_time = 0.0`, and click (1 launch). Then:
   - `update(0.05)`: `base.rapid_fire is False` and `cooldown_time == pytest.approx(0.05)`;
   - `update(0.06)`: `can_fire() is True`;
   - the next click sets `cooldown_time == BASE_COOLDOWN_TIME`.
8. [test] **Sound follows each window.** `main_game` with a spy. For each `t` in
   `(10.0, 65.0, 100.0, 125.0, 150.0, 185.0)`:
   - bring to `t`;
   - set `base.cooldown_time = 0.0`;
   - clear `calls`;
   - `handle_actions(FIRE)`.

   `calls` is `["launch"]` for 10, 100 and 150, and `["laser"]` for 65, 125 and 185.
   Each click plays exactly one sound.
9. [test] **Pause freezes a later window.** On `main_game`, set `game_time = 125.0` and
   call `update(DT_DEFAULT)`. Pause with `handle_actions({"toggle_pause": True})`, run 600
   `handle_actions({})` calls, then resume. `game_time` hasn't changed,
   `base.rapid_fire is True`, one more `update(DT_DEFAULT)` keeps it `True`, and a click
   while paused launched nothing.
10. [test] **A new game starts the cycle again.** On `main_game`, bring to 125.0 (window
    open), then `start_game()`. Now `game_time == 0.0`, `base.rapid_fire is False` and
    `rapid_fire_active() is False`. Bringing to 30.0 still gives `False`. Bringing to 60.1
    gives `base.rapid_fire is True`.
11. [test] **Tower colour in rendered frames.** On `main_game`, bring to each `t` and call
    `draw()`. Then sample `game.screen` at `base.get_bounds().center` and at
    `base.barrel_rect().center`:
    - both are `LAUNCHER_RAPID_FIRE_COLOR` for `t` in `(125.0, 185.0)`;
    - both are `COLOR_WHITE` for `t` in `(100.0, 135.0)`.
12. [test] **Long game, no audio, no crash.** With the 013 no-audio setup
    (`pygame.mixer.get_init` → `None`, `pygame.mixer.init` raises `pygame.error`,
    `CONFIG_PATH` patched): start a new `MainGame`, set `last_spawn_time = inf`, and bring
    to 119.5. Then run 120 frames of `handle_actions(FIRE)` + `update(DT_DEFAULT)` +
    `check_collisions()` + `draw()`. This crosses into the second window. Nothing raises,
    and `base.rapid_fire is True` at the end.
13. [test] **Nothing else changed.**
    - The whole existing suite, including every test in `tests/test_rapid_fire.py` and
      `tests/test_wave_counter.py`, passes with no edits, using the README test command.
    - The real `config.json` is byte-for-byte the same before and after the new test file
      runs.
    - `git diff --stat` shows no change to `entities/base.py` or `systems/sound.py`.
14. [visual] **Red tower in the second window.** Render a `main_game` frame with `draw()`
    at `game_time` about 125 (reached through `update()`), with a few defence missiles in
    flight. The launcher body and barrel at bottom centre are solid red
    (`LAUNCHER_RAPID_FIRE_COLOR`). The reload bar is in its usual place and colours. The HUD
    reads `WAVE: 5` to the left of the score.
15. [visual] **White between windows.** The same game rendered at about 135 s shows a white
    (`COLOR_WHITE`) tower that looks the same as a frame at about 10 s, with the HUD reading
    `WAVE: 5`.

## Touch points
- `game/constants.py`: add `RAPID_FIRE_INTERVAL = 60.0` to the "Rapid-fire window" block
  and update that block's heading comment.
- `systems/game_loop.py`, `MainGame.rapid_fire_active()`: change the condition and the
  docstring. No other line in `game_loop.py` should change.
- `README.md`: rewrite the one Gameplay sentence.
- `tests/test_repeat_rapid_fire.py` (new). It may copy the small helpers from
  `tests/test_rapid_fire.py` (`spy`, `launches`, `at_time`) rather than importing them.

Expected diff: about 5 lines in `game_loop.py`, 2 in constants, 1 in README, and 150–200
lines of tests.

## Notes for reviewers
- **code:**
  - `rapid_fire_active()` must still be worked out only from `game_time`. There must be no
    new "last window" attribute, counter or wall-clock call (`time.time()`,
    `pygame.time.get_ticks()`). Any of those would break pause and restart.
  - Check the `game_time < RAPID_FIRE_START_TIME` guard. Without it, Python's `%` on a
    negative number would open a window at [0, 10).
  - Float edges: `130.0` must give `False` and `129.99` `True` (criterion 2). Use plain `%`
    with `<`; don't round.
  - No edits to `entities/base.py`. If the builder thinks they are needed, the 013
    off-to-on handling in `set_rapid_fire()` has a bug that should be reported, not
    worked around.
- **security:** No new file, network or config I/O. The new tests patch `CONFIG_PATH`
  before building any `MainGame`.
- **ux:**
  - The window now opens 10 s out of every 60 for the rest of the game. That is about 17%
    of play time at a 0.1 s reload, which may make long games much easier. Spawning still
    speeds up over time (`BASE_SPAWN_INTERVAL / (game_time/60 + 1)`, down to
    `MIN_SPAWN_INTERVAL`). Play to about 3 minutes and judge whether later windows still
    feel like a reward and not a rescue. Tuning is a follow-up.
  - Players still get no warning before a window opens or closes. With repeating windows a
    countdown is a more useful follow-up than it was in 013, but it is out of scope here.
  - A window opens at the same moment as every other wave change (WAVE 3, 5, 7, ...). See
    whether this reads as intended or confusing.
- **ui:** Check frames 14 and 15. Only the tower body and barrel change colour. The reload
  bar, city and HUD (score and wave) look the same in and out of the window.
