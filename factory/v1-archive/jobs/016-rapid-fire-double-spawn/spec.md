# 016-rapid-fire-double-spawn: Twice as many incoming missiles while rapid fire is on

## Problem
Job 013 added a rapid-fire window (60 s to 70 s of `game_time`) in which the launcher
reloads in 0.1 s instead of 1.5 s. Enemy spawning doesn't change during the window, so it
is free time with very little to shoot at. The player wants the window to be a fight as
well as a reward: while rapid fire is on, twice as many incoming missiles should come down.

**What "double the amount" means in this spec.** Today `MainGame.update()` spawns **one**
missile each time `game_time - last_spawn_time >= current_interval`, where
`current_interval = max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL / (game_time / 60 + 1))`.
That ramp hits its 2.0 s floor at 45 s, so at every rapid-fire window the interval is
2.0 s. This job doubles the **spawn rate**, not the number per spawn: while rapid fire is
on, the interval is the normal ramped-and-floored interval divided by
`RAPID_FIRE_SPAWN_RATE_MULTIPLIER` (2), so 1.0 s during the window. Each spawn still makes
exactly one missile, and one `update()` call still spawns at most one. So a 10 s window
gets 10 missiles where the same 10 s outside a window gets 5. Doubling the count per spawn
was rejected for two reasons. Two missiles spawned in the same frame often aim at the same
building and look like one, and it would break the "at most one spawn per frame" rule that
the existing tests rely on.

## Scope
- **Spawn interval** (`systems/game_loop.py`, `MainGame`):
  - New method `current_spawn_interval()` that returns the interval `update()` uses this
    frame:
    `base = max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL / (self.game_time / 60.0 + 1.0))`
    (the current formula, unchanged), then `base / RAPID_FIRE_SPAWN_RATE_MULTIPLIER` if
    `self.rapid_fire_active()` is true, otherwise `base`.
  - **Ramp order:** the `MIN_SPAWN_INTERVAL` floor is applied *before* the multiplier.
    During a window the interval can go below `MIN_SPAWN_INTERVAL` (to 1.0 s), and that is
    intended. If the floor were applied afterwards, the doubling would do nothing at
    60 s and later.
  - In `update()`, replace the inline `current_interval = max(...)` expression (the two
    lines after `add_survival_time`) with `current_interval = self.current_spawn_interval()`.
    The spawn test (`>=`), the single `spawn_incoming_missile()` call and
    `self.last_spawn_time = self.game_time` stay exactly as they are. Don't add catch-up
    loops or second spawns.
  - Whether rapid fire is on is decided **only** by calling `self.rapid_fire_active()`.
    Don't compare `game_time` with `RAPID_FIRE_START_TIME` or `RAPID_FIRE_DURATION` anywhere
    in this job. Then, when job 015 merges (it changes only the body of
    `rapid_fire_active()` so the window repeats at 120–130, 180–190, ...), the doubled spawn
    rate follows every window with no further edits.
  - `rapid_fire_active()` itself must **not** be edited (body, docstring or position).
  - Put `current_spawn_interval()` straight after `spawn_incoming_missile()` (before
    `spawn_new_building()`), **not** next to `rapid_fire_active()`, so this branch and 015
    don't touch neighbouring lines.
- **Window edges, from the rule above** (no extra code needed):
  - On entry, the first doubled spawn comes as soon as `game_time - last_spawn_time >= 1.0`.
    That can be the first frame of the window if the last spawn was at least 1.0 s ago.
  - On exit, the interval goes back to 2.0 s, still measured from the last spawn, so there
    is no burst and no gap longer than the normal interval.
  - Pause: `update()` doesn't run while paused, so no spawns happen and `game_time` doesn't
    move. After resuming inside a window the doubled rate carries on.
  - `start_game()` already sets `game_time = 0.0` and `last_spawn_time = 0.0`, so a new
    game starts at `BASE_SPAWN_INTERVAL` with no doubling.
- **Constant** (`game/constants.py`): add `RAPID_FIRE_SPAWN_RATE_MULTIPLIER = 2` in the
  `# Difficulty settings` block, straight after `MIN_SPAWN_INTERVAL`, with a comment like
  "Enemy spawn rate multiplier while rapid fire is on". Don't put it in the "Rapid-fire
  window" block: job 015 edits that block's heading.
- **README**: add one bullet to "Features", straight after "Difficulty ramps up
  continuously as the game progresses". It should say that while the launcher's
  rapid-fire window is open, enemy missiles come twice as often. Do **not** edit the
  Gameplay paragraph: job 015 rewrites the rapid-fire sentence there, and that paragraph
  is a single line, so any edit to it would conflict.
- **Tests**: new file `tests/test_rapid_fire_spawns.py`. No existing test is edited.

## Out of scope
- Changing `rapid_fire_active()`, the window times, or making the window repeat (that is
  job 015).
- Spawning more than one missile per spawn event, faster or differently aimed missiles, or
  new enemy types during the window.
- Changing the ramp formula itself, `MIN_SPAWN_INTERVAL`, `BASE_SPAWN_INTERVAL`, or wiring
  up the unused `DIFFICULTY_RAMP_RATE` constant or `self.spawn_interval` attribute.
- Any warning, HUD text, colour or sound that tells the player spawns have sped up.
- Score changes (for example bonus points for kills during the window).
- Saving anything to `config.json`, and GAME_DESIGN.md edits.

## Acceptance criteria
Terms:
- `main_game` is the conftest fixture (playing, `CONFIG_PATH` patched,
  `last_spawn_time = inf`).
- A **spawn recorder** is `times = []` plus
  `monkeypatch.setattr(game, "spawn_incoming_missile", lambda: times.append(game.game_time))`.
  It records the `game_time` of every spawn.
- **Step from t0** means `game.game_time = t0`, `game.last_spawn_time = t0`, then repeated
  `game.update(0.25)` calls. 0.25 and every time used below are exact in binary floating
  point, so the spawn times can be compared with `==`.

1. [test] **Constant.** `RAPID_FIRE_SPAWN_RATE_MULTIPLIER == 2`. `BASE_SPAWN_INTERVAL == 3.5`
   and `MIN_SPAWN_INTERVAL == 2.0` are unchanged.
2. [test] **Interval values.** On `main_game`, set `game_time` directly and call
   `current_spawn_interval()`:
   - `0.0` gives `3.5`, `30.0` gives `pytest.approx(3.5 / 1.5)`, and `45.0`, `59.99`,
     `70.0` and `100.0` give `2.0` (ramp unchanged outside the window);
   - `60.0`, `65.0` and `69.99` give `1.0` (floored ramp ÷ 2 inside the window).
3. [test] **Rapid fire is read only through `rapid_fire_active()`.** On `main_game`:
   - with `monkeypatch.setattr(game, "rapid_fire_active", lambda: True)` and `game_time`
     `0.0` the interval is `1.75`, and at `30.0` it is `pytest.approx(3.5 / 1.5 / 2)`. This
     shows the multiplier works on the ramped value and doesn't depend on the 60 s start;
   - with it patched to `lambda: False` and `game_time = 65.0` the interval is `2.0`;
   - with it patched to the 015 rule
     `lambda: game.game_time >= 60.0 and (game.game_time - 60.0) % 60.0 < 10.0`, the
     interval is `1.0` at `125.0` and `185.0` and `2.0` at `100.0` and `130.0`.
4. [test] **Twice as many spawns across a window.** With a spawn recorder:
   - step from `59.75` 40 times (to `69.75`, every step inside the window):
     `times == [60.75, 61.75, ..., 69.75]` (10 spawns, 1.0 s apart);
   - on a fresh recorder, step from `89.75` 40 times (to `99.75`, outside the window under
     both 013 and 015): `times == [91.75, 93.75, 95.75, 97.75, 99.75]` (5 spawns);
   - so the window has exactly `RAPID_FIRE_SPAWN_RATE_MULTIPLIER` times as many spawns.
5. [test] **Entering the window.** With a spawn recorder, step from `59.0` 12 times (to
   `62.0`): `times == [60.0, 61.0, 62.0]`. The 1.0 s since the last spawn is enough at the
   first window frame.
6. [test] **Leaving the window.** With a spawn recorder, step from `69.0` 12 times (to
   `72.0`): `times == [71.0]`. There is no spawn at `70.0`, even though 1.0 s has passed,
   because the window has closed. The next spawn is the normal 2.0 s after the last.
7. [test] **Still one missile per spawn and per frame.**
   - Real spawns (no recorder): step from `59.75` 8 times (to `61.75`), and
     `len(game.incoming_missiles) == 2`. Step from `89.75` 8 times (to `91.75`) after
     `game.incoming_missiles = []`, and the length is `1`.
   - With a recorder, `game_time = 60.0`, `last_spawn_time = 0.0`, one `update(5.0)`
     records exactly 1 spawn.
8. [test] **Pause freezes the doubled rate.** With a spawn recorder on `main_game`: set
   `game_time = 65.0` and `last_spawn_time = 65.0`. Pause with
   `handle_actions({"toggle_pause": True})`, run 600 `handle_actions({})` calls, then resume
   with `handle_actions({"toggle_pause": True})`. `times == []` and `game_time == 65.0`.
   Four more `update(0.25)` calls then record `times == [66.0]`.
9. [test] **New game resets.** On `main_game`, step from `59.75` 8 times (inside the
   window), then `start_game()`. `game_time == 0.0`, `last_spawn_time == 0.0` and
   `current_spawn_interval() == BASE_SPAWN_INTERVAL`.
10. [test] **Launcher behaviour unchanged.** After stepping from `59.75` 4 times,
    `game.base.rapid_fire is True` and `game.base.rapid_fire == game.rapid_fire_active()`.
    After stepping from `89.75` 4 times both are `False`.
11. [test] **Nothing else changed.**
    - The whole existing suite passes with no edits, using the README test command. That
      includes `tests/test_game_states.py::test_spawns_run_on_game_time` (first spawn at
      about 3.32 s) and every test in `tests/test_rapid_fire.py`.
    - The real `config.json` is byte-for-byte the same before and after.
    - `git diff` shows no change inside `MainGame.rapid_fire_active()` and none to
      `entities/` or `systems/sound.py`.
12. [visual] **A busier window.** Seed `random.seed(0)`. On `main_game`, step from `59.75`
    to `66.0` calling `check_collisions()` after each `update()`, then `draw()`. On a fresh
    `main_game` with the same seed, do the same from `89.75` to `96.0`. In the first frame
    the tower is red (`LAUNCHER_RAPID_FIRE_COLOR`) and clearly more red (`COLOR_RED`)
    enemy missile heads with orange-to-grey trails are in the sky than in the second
    frame, where the tower is white (`COLOR_WHITE`). The HUD, city and reload bar look the
    same in both.

## Touch points
- `game/constants.py`: `RAPID_FIRE_SPAWN_RATE_MULTIPLIER = 2` in `# Difficulty settings`,
  after `MIN_SPAWN_INTERVAL`.
- `systems/game_loop.py` (`MainGame`):
  - new `current_spawn_interval()`, placed after `spawn_incoming_missile()`;
  - in `update()`, the two-line `current_interval = max(...)` expression becomes one call.
  - No other lines change. In particular, `rapid_fire_active()` stays exactly as it is.
- `README.md`: one new Features bullet.
- `tests/test_rapid_fire_spawns.py` (new).

Expected diff: about 12 lines in `game_loop.py`, 1 in constants, 1 in README, and 150–200
lines of tests.

## Notes for reviewers
- **code:**
  - Check that `current_spawn_interval()` gets the window state only from
    `self.rapid_fire_active()`, and that no `RAPID_FIRE_START_TIME` / `RAPID_FIRE_DURATION`
    / `game_time %` logic is copied into the spawn code (criterion 3 tests this by
    patching). Using `self.base.rapid_fire` would also be acceptable, because `update()`
    syncs it just before, but the spec asks for `rapid_fire_active()` so the method works
    when called on its own.
  - The floor must come before the multiplier (criterion 2: `1.0` at 65 s, not `2.0`).
  - The order in `update()` must stay: `game_time += dt`, `set_rapid_fire`,
    `add_survival_time`, interval, then spawn. So the interval uses this frame's
    `game_time`.
  - Merge safety with 015: the new method must not sit next to `rapid_fire_active()`, the
    constant must not go in the rapid-fire block, and the README Gameplay line must not be
    touched. After both branches merge, criterion 3's 015 case and 015's own tests should
    both pass with no edits.
  - No reformatting of nearby code. The unused `self.spawn_interval` and
    `DIFFICULTY_RAMP_RATE` stay as they are.
- **security:** No new file, network or config I/O. Tests patch `CONFIG_PATH` (through
  `main_game`) before any `MainGame` is built. Spawning stays bounded at one missile per
  frame, so a huge `dt` can't cause a flood (criterion 7).
- **ux:**
  - At 1.0 s per spawn against a 0.1 s reload, the window should still favour the player.
    But once 015 merges, about 17% of play time has double spawns. Play past 2:00 and
    judge whether the windows feel exciting rather than punishing.
  - The player gets no warning that spawns have sped up. The red tower is the only hint.
    Check that the link between "tower red" and "more missiles" is clear in play.
  - At window exit, the missiles that spawned during the window are still falling while
    reload is back to 1.5 s. Check that the last 2–3 seconds after a window aren't unfairly
    hard.
- **ui:** Check frame 12. Nothing is drawn differently apart from the number of enemy
  missiles. The tower colour comes from 013 and is not changed here.
