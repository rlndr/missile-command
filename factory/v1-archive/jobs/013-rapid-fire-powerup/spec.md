# 013-rapid-fire-powerup: Rapid-fire launcher window after one minute

## Problem
The launcher always reloads in `BASE_COOLDOWN_TIME` (1.5 s), so a run plays the same from
start to finish. The player wants a reward for holding out: after 1 minute of play the
launcher tower turns red for 10 seconds, and during that time it can fire a missile every
0.1 s, each with its own laser-like sound. After the 10 seconds the launcher goes back to
normal. GAME_DESIGN.md §14 already lists power-ups as a future enhancement.

## Scope
- **Rapid-fire window** (`systems/game_loop.py`):
  - New method `MainGame.rapid_fire_active()` returns `True` exactly when
    `RAPID_FIRE_START_TIME <= self.game_time < RAPID_FIRE_START_TIME + RAPID_FIRE_DURATION`
    (that is, 60.0 s up to but not including 70.0 s of play time).
  - `game_time` only goes up in `update()`, which only runs while `STATE_PLAYING`. So pause
    time doesn't count toward the 60 s, and pausing during the window freezes the time left.
  - In `update()`, right after `self.game_time += dt` and before `self.base.update(dt)`, call
    `self.base.set_rapid_fire(self.rapid_fire_active())`.
  - The window happens once per game. `start_game()` already sets `game_time = 0.0` and calls
    `base.reset()`, which turns rapid fire off, so each new game gets its own window at 60 s.
- **Launcher** (`entities/base.py`, `DefensiveBase`):
  - New attribute `rapid_fire` (bool), `False` after `__init__()` and after `reset()`.
  - New attribute `cooldown_length`: how long the current reload lasts in total.
    `BASE_COOLDOWN_TIME` after `__init__()` and `reset()`.
  - New method `set_rapid_fire(on)`:
    - sets `rapid_fire = bool(on)`;
    - when it switches on and `cooldown_time > RAPID_FIRE_COOLDOWN_TIME`, sets both
      `cooldown_time` and `cooldown_length` to `RAPID_FIRE_COOLDOWN_TIME`, so a slow reload
      that was already running doesn't eat into the window;
    - when it switches off, the reload that is running finishes as it is (at most 0.1 s).
  - `start_cooldown()` sets `cooldown_time` and `cooldown_length` to
    `RAPID_FIRE_COOLDOWN_TIME` while `rapid_fire` is on, otherwise to `BASE_COOLDOWN_TIME`.
    It still does nothing while offline.
  - `reload_progress()` and the `cooldown_ratio` set in `update()` divide by `cooldown_length`
    instead of `BASE_COOLDOWN_TIME`. Everything else about them stays the same: clamped to
    `[0, 1]`, 0.0 when offline, and full only when `can_fire()`.
  - `draw_base()`: while active and `rapid_fire` is on, the body and barrel are filled with
    `LAUNCHER_RAPID_FIRE_COLOR` instead of `active_color`. The offline look and the reload bar
    are unchanged.
- **Firing** (`MainGame.spawn_defense_missile`): still one missile per left click, and only
  when `can_fire()`. When a missile is actually launched it plays `"laser"` if
  `self.base.rapid_fire` is on, and `"launch"` otherwise. Exactly one sound per launch.
- **Laser sound** (`systems/sound.py`, `game/constants.py`):
  - Add `"laser"` to the end of `SOUND_NAMES`.
  - Add the recipe `"laser": (_SWEEP, SOUND_LASER_SWEEP)` to `_RECIPES`, with
    `SOUND_LASER_SWEEP = (1800, 300, 0.08)`: a fast falling square-wave "pew", built with the
    existing `square_sweep`.
  - The sound is 0.08 s long, shorter than the 0.1 s rapid-fire reload, so back-to-back shots
    never overlap.
  - Because it goes through `SoundSystem`, it is built with the other sounds, silenced by
    mute (M), and does nothing when `available` is False. No new error handling is needed.
- **README**: one sentence in "Gameplay" after the reload-bar sentence, saying that after
  60 seconds of play the launcher turns red for 10 seconds and can fire every 0.1 s with a
  laser sound.
- **Tests**:
  - New file `tests/test_rapid_fire.py`.
  - In `tests/test_sound.py`, change only two things: the `SOUND_NAMES` expectation in
    `test_constants` (add `"laser"` at the end) and a `"laser": SOUND_LASER_SWEEP[2]` entry in
    `DURATIONS`, plus the import those need. No other existing test is edited.

## Out of scope
- Making the window repeat (for example every minute), random power-up pickups, or other
  power-up types such as double shots or slower enemies.
- Hold-the-mouse-button auto-fire. Each shot still needs its own click.
- A HUD countdown, an "about to end" warning, flashing or pulsing the tower, a screen tint,
  or recolouring defence missiles or explosions during the window.
- Start/pause menu text about the power-up, and GAME_DESIGN.md edits.
- Saving anything about the power-up to `config.json`.
- Any change to scoring, enemy spawning or difficulty during the window.

## Acceptance criteria
Terms used below:
- `FIRE = {"fire_missile": (400, 300)}`.
- A **spy** is `calls = []` plus
  `monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)`.
- `main_game` is the existing conftest fixture (playing, `CONFIG_PATH` patched, no random
  spawns).
- **Enter the window** means `game.game_time = 59.9` then `game.update(0.2)`, which leaves
  `game_time` at about 60.1.
- **Launches** are counted with a spy (number of `"laser"` / `"launch"` calls) or by
  comparing `len(defense_missiles)` straight before and after one `handle_actions()` call.
  Don't use `len(defense_missiles)` across `update()` calls, because missiles that have
  detonated are removed.

1. [test] **Constants.** `RAPID_FIRE_START_TIME == 60.0`, `RAPID_FIRE_DURATION == 10.0`,
   `RAPID_FIRE_COOLDOWN_TIME == 0.1`, `LAUNCHER_RAPID_FIRE_COLOR == COLOR_RED`,
   `SOUND_LASER_SWEEP == (1800, 300, 0.08)`, and
   `SOUND_NAMES == ("launch", "explosion", "intercept", "impact", "game_over", "laser")`.
2. [test] **Window boundaries.** On `main_game`, setting `game_time` directly and calling
   `rapid_fire_active()` gives `False` for `0.0`, `59.99` and `70.0`, and `True` for `60.0`,
   `65.0` and `69.99`.
3. [test] **The launcher follows the window.** On `main_game`:
   - `game.base.rapid_fire is False` after `start_game()`;
   - after entering the window, `game.base.rapid_fire is True`;
   - after `game.game_time = 69.9` then `update(0.2)`, `game.base.rapid_fire is False`;
   - after every one of those `update()` calls, `game.base.rapid_fire == game.rapid_fire_active()`.
4. [test] **Fast reload during the window.** On `main_game`, enter the window and set
   `game.base.cooldown_time = 0.0`. Then:
   - `handle_actions(FIRE)` launches exactly 1 missile, and
     `base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)`;
   - after `update(0.05)`, `handle_actions(FIRE)` launches nothing;
   - after a further `update(0.06)`, `handle_actions(FIRE)` launches 1 missile;
   - repeating `update(0.11)` then `handle_actions(FIRE)` 20 times (still inside the window)
     gives exactly 20 launches.
5. [test] **Normal reload outside the window.** On `main_game` with `game_time` at about 10:
   - `handle_actions(FIRE)` sets `base.cooldown_time == BASE_COOLDOWN_TIME`;
   - a second `handle_actions(FIRE)` after `update(0.2)` launches nothing.
   - After the window ends (`game_time = 69.9`, `update(0.2)`, then `update(0.2)` again so
     the last short reload is over), a shot sets `cooldown_time == BASE_COOLDOWN_TIME` again.
6. [test] **Running reload is cut short on entry.** On a fresh `DefensiveBase()`, call
   `reset()` and `start_cooldown()` (1.5 s), then `set_rapid_fire(True)`.
   `cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)`,
   `cooldown_length == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)`, and `0.0 <= reload_progress() <= 1.0`.
   After `update(0.1)`, `can_fire() is True` and `reload_progress() == 1.0`. If
   `cooldown_time` was already `0.05`, `set_rapid_fire(True)` leaves it at `0.05`.
7. [test] **Reload bar uses the current reload length.** On a `DefensiveBase()` with
   `reset()`, `set_rapid_fire(True)` and `start_cooldown()`: `reload_progress() == 0.0`, and
   after `update(0.05)` it is `pytest.approx(0.5)`. With `set_rapid_fire(False)`, `reset()` and
   `start_cooldown()`, `update(0.375)` gives `pytest.approx(0.25)`, the same as today.
8. [test] **Reset clears rapid fire.** `base.set_rapid_fire(True)` then `base.reset()` gives
   `rapid_fire is False`, `cooldown_length == BASE_COOLDOWN_TIME` and `can_fire() is True`.
   On `main_game`, enter the window, then `start_game()`: `base.rapid_fire is False`,
   `rapid_fire_active() is False` and `game_time == 0.0`.
9. [test] **Pause freezes the window.** On `main_game`, set `game_time = 65.0` and call
   `update(DT_DEFAULT)`. Then `handle_actions({"toggle_pause": True})`, run 600
   `handle_actions({})` calls (about 10 s of paused frames), and resume with
   `handle_actions({"toggle_pause": True})`. `game_time` is unchanged by the paused frames,
   `base.rapid_fire is True`, and one more `update(DT_DEFAULT)` keeps it `True`. Clicking
   while paused launches nothing.
10. [test] **Laser sound on rapid-fire shots.** `main_game` with a spy:
    - at `game_time` about 10, `handle_actions(FIRE)` gives `calls == ["launch"]`;
    - after `start_game()`, entering the window, and `base.cooldown_time = 0.0`,
      `handle_actions(FIRE)` adds exactly `"laser"` and no `"launch"`;
    - a click during the 0.1 s reload adds nothing;
    - with `state = STATE_PAUSED`, a click adds nothing.
11. [test] **Laser sound is synthesised like the others.**
    - For `channels` in `(1, 2)`, `len(sound_bytes("laser", 22050, channels)) == round(0.08 * 22050) * 2 * channels`.
    - `s = square_sweep(*SOUND_LASER_SWEEP, 22050)`: `abs(s[0]) == round(SOUND_VOLUME * 32767)`
      and `s[-1] == 0`.
    - The pitch falls: the window `[0, n/5)` of `s` has more than 1.5 times as many sign
      changes as the window `[3n/5, 4n/5)`.
    - `SOUND_LASER_SWEEP[2] < RAPID_FIRE_COOLDOWN_TIME`.
12. [test] **Laser sound respects mute and no-audio.**
    - Under the dummy driver, `"laser" in main_game.sound.sounds`, its `get_length()` is
      `pytest.approx(0.08, abs=0.02)`, and `play("laser") is True`. Skip only if
      `pygame.mixer` is missing from the build.
    - After `toggle_mute()`, `play("laser") is False`.
    - With `pygame.mixer.get_init` patched to return `None` and `pygame.mixer.init` to raise
      `pygame.error`, a new `MainGame()` has `sound.available is False`. Starting it, entering
      the window, and running 120 frames of `handle_actions(FIRE)` + `update(DT_DEFAULT)` +
      `check_collisions()` + `draw()` raises nothing.
13. [test] **Tower colour from a rendered surface.** Draw a `DefensiveBase` with `draw_base()`
    on a black screen-sized surface. Sample the pixel at the centre of `get_bounds()` and the
    one at the centre of `barrel_rect()`:
    - with `rapid_fire` False both are `COLOR_WHITE`;
    - after `set_rapid_fire(True)` both are `LAUNCHER_RAPID_FIRE_COLOR`;
    - after `set_rapid_fire(False)` both are `COLOR_WHITE` again;
    - with `is_active = False` and `rapid_fire` True, the body centre is `COLOR_GRAY` (offline
      look wins).
14. [test] All existing tests pass, with only the two `tests/test_sound.py` edits listed in
    Scope. The full suite passes with the README command, and the real `config.json` is
    byte-for-byte unchanged.
15. [visual] **Red tower in play.** Render a `main_game` frame with `draw()` at
    `game_time` about 65 (entered via `update()`), with a few defence missiles in flight. The
    launcher tower body and barrel at the bottom centre, between the two city halves, are
    solid red (`LAUNCHER_RAPID_FIRE_COLOR`). The reload bar is still under it in its usual
    place and colours, and the score HUD is unchanged.
16. [visual] **Back to normal.** The same game rendered after `game_time` passes 70 shows the
    tower white (`COLOR_WHITE`) again, identical to a frame at `game_time` about 10.

## Touch points
- `game/constants.py`:
  - next to the launcher / cooldown constants: `RAPID_FIRE_START_TIME = 60.0` (seconds of
    play before the window opens), `RAPID_FIRE_DURATION = 10.0` (window length in seconds),
    `RAPID_FIRE_COOLDOWN_TIME = 0.1` (reload during the window),
    `LAUNCHER_RAPID_FIRE_COLOR = COLOR_RED` (tower body and barrel during the window);
  - in the `# Sound` section: `SOUND_LASER_SWEEP = (1800, 300, 0.08)` (start Hz, end Hz,
    seconds), and `"laser"` appended to `SOUND_NAMES`.
- `entities/base.py` (`DefensiveBase`): `__init__`, `reset`, new `set_rapid_fire`,
  `start_cooldown`, `update`, `reload_progress`, `draw_base`.
- `systems/game_loop.py` (`MainGame`): new `rapid_fire_active`, `update` (one call to
  `set_rapid_fire`), `spawn_defense_missile` (choose `"laser"` or `"launch"`).
- `systems/sound.py`: one new `_RECIPES` entry. No other change is expected.
- `README.md`: one Gameplay sentence.
- `tests/test_rapid_fire.py` (new), and the two small edits to `tests/test_sound.py`.

Expected diff: about 30 lines in `entities/base.py`, 10 in `game_loop.py`, 1 in `sound.py`,
8 of constants, 1 of README, and 200–250 lines of tests.

## Notes for reviewers
- **code:**
  - There is a single source of truth for whether the window is open:
    `MainGame.rapid_fire_active()`, derived from `game_time`. `update()` copies it onto the
    base each frame. Check there is no second timer or wall-clock (`time.time()`,
    `pygame.time.get_ticks()`) that would keep running while paused.
  - `cooldown_length` must be set in every place that sets a new reload (`start_cooldown`,
    the clamp in `set_rapid_fire`, `reset`, `__init__`), so `reload_progress()` never goes
    outside `[0, 1]` or reads as ready while `can_fire()` is False. The existing
    `test_cooldown_indicator.py` and `test_reset_cooldown.py` tests must pass unedited.
  - Sound choice uses `self.base.rapid_fire` at the moment of the click, which matches the
    reload the shot gets from `start_cooldown()`. The laser shot and its 0.1 s reload must
    always go together.
  - `"laser"` is added to `SOUND_NAMES`, so `SoundSystem.play("laser")` must not raise
    `KeyError`, and the cached `sound_bytes` path must build it. Keep the change in
    `sound.py` to the recipe table.
  - Keep `game_loop.py` edits to the listed lines. No reformatting.
- **security:** No new file, network or config I/O. Tests patch `CONFIG_PATH` before
  building a `MainGame`.
- **ux:**
  - The red tower is the only signal the window is open, so it has to be obvious next to
    the white buildings and blue sky. `COLOR_RED` is also the enemy missile colour; check
    that the tower still reads as the player's launcher and not a threat.
  - There is no warning before the window ends. The player finds out when the tower turns
    white and the next click waits 1.5 s. That is acceptable for this slice; a countdown is
    a possible follow-up.
  - Clicking ten times a second is hard. The 0.1 s figure is a ceiling, not something the
    player must reach. Hold-to-fire is deliberately out of scope.
  - With speakers, run `python3 main.py`, survive to 60 s, and confirm the laser "pew" is
    clearly different from the normal launch sweep, is short, has no click at the end, and
    isn't harsh when fired quickly. M must silence it.
- **ui:** Check frames 15 and 16. Only the tower body and barrel change colour. The reload
  bar, its position, the city and the HUD must look exactly as they do outside the window.
