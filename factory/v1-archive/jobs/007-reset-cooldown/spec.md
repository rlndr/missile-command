# 007-reset-cooldown: Launcher is ready to fire at the start of every game

## Problem
`DefensiveBase.__init__` sets `cooldown_time = BASE_COOLDOWN_TIME` (1.5 s), and
`MainGame.start_game()` never touches `self.base`. So on the first game, clicks in the first
1.5 s of play do nothing. On a restart from GAME_OVER the launcher keeps whatever cooldown it
had when the last building fell, so the first click of the new game can be ignored for no
visible reason. The existing tests hide this by setting `base.cooldown_time = 0` by hand
(`tests/test_game_states.py`, `tests/test_missiles_explode.py`). `MainGame` also carries a
`self.base_cooldown = 0.0` attribute that nothing reads.

## Scope
- **`DefensiveBase.reset()`** (new, `entities/base.py`). It puts the launcher in its
  ready state: `cooldown_time = 0.0`, `cooldown_ratio = 0.0`, `is_active = True`. It does not
  move the base or change its size or render offsets.
- **`MainGame.start_game()`** calls `self.base.reset()`. It resets the existing `self.base`
  object in place and does not build a new `DefensiveBase`. `start_game()` is the single path
  for both SPACE on the start screen and SPACE on GAME_OVER, so both are covered.
- **Pause keeps the cooldown.** Pause and resume (ESC) must not call `reset()` or change
  `cooldown_time`. Otherwise ESC twice would skip the reload. `base.update(dt)` already runs
  only from `update()`, so the cooldown is frozen while paused. Keep it that way.
- **Firing rules are unchanged.** `spawn_defense_missile()` still checks `can_fire()` and
  then calls `start_cooldown()`. A click in the same `handle_actions()` call as the SPACE that
  starts the game still does not fire (the existing "state was PLAYING before and after"
  rule).
- **Dead attribute.** Delete `self.base_cooldown = 0.0` from `MainGame.__init__`.
- **Tests.** Add a new file `tests/test_reset_cooldown.py`. Do not edit the existing test
  files. Their `cooldown_time = 0` lines become redundant but harmless.

## Out of scope
- The cooldown indicator bar under the launcher (the next backlog item, "Launcher cooldown
  indicator"). This job only makes sure `cooldown_ratio` exists and is `0.0` after `reset()`.
- Changing `DefensiveBase.__init__`. A launcher built in `__init__` keeps starting at
  `BASE_COOLDOWN_TIME`. It never fires before `start_game()`, so this is not visible.
- Changing `BASE_COOLDOWN_TIME` or how the cooldown counts down.
- Knocking the launcher offline (`is_active = False`). Nothing does this today. `reset()`
  restores `is_active = True` only so a future knock-out can't carry into a new game.
- Removing the now-redundant `cooldown_time = 0` lines from the existing tests.
- README and GAME_DESIGN.md changes. The controls and rules players read are unchanged.

## Acceptance criteria
Tests patch `systems.score.CONFIG_PATH` to a file under `tmp_path` before building a
`MainGame`, as the `main_game` fixture does. `FIRE` means `{"fire_missile": (400, 300)}`.
A **start-screen game** is a `MainGame()` built with that patch, left in `STATE_START`, with
no `start_game()` call and no change to `base.cooldown_time`. Note that the `fresh_game`
fixture in `tests/test_game_states.py` zeroes the cooldown, so do not reuse it here.

1. [test] **First click of the first game fires.**
   - On a start-screen game, `base.cooldown_time == BASE_COOLDOWN_TIME` before anything runs.
   - `handle_actions({"start": True})` gives `state == STATE_PLAYING`,
     `base.cooldown_time == 0.0` and `base.can_fire() is True`.
   - Then `handle_actions(FIRE)`, with no `update()` call in between, gives
     `len(defense_missiles) == 1` and `base.cooldown_time == BASE_COOLDOWN_TIME`.
2. [test] **First click after a restart fires.**
   - Start a game from a start-screen game and fire once with `FIRE`. Call
     `update(0.3)` once, so `base.cooldown_time == pytest.approx(BASE_COOLDOWN_TIME - 0.3)`.
   - Mark every building destroyed, then call `check_collisions()` and `check_game_over()`.
     `state == STATE_GAME_OVER` and the cooldown is still above 0.
   - `handle_actions({"start": True})` gives `base.cooldown_time == 0.0`. A following
     `handle_actions(FIRE)` gives `len(defense_missiles) == 1`. The list was cleared by the
     restart, so this is the new game's missile.
3. [test] **Every way into a game resets it.** Parametrise over the starting state
   (`STATE_START`, `STATE_GAME_OVER`) and the leftover cooldown (`0.01`, `0.75`,
   `BASE_COOLDOWN_TIME`). Set `base.cooldown_time` to that value and
   `base.is_active = False`, then call `handle_actions({"start": True})`. Afterwards
   `base.cooldown_time == 0.0`, `base.cooldown_ratio == 0.0`, `base.is_active is True` and
   `base.can_fire() is True`.
4. [test] **Same launcher object.** `base = game.base`, then `game.start_game()`; afterwards
   `game.base is base`, and `base.position == Vector2(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)`.
5. [test] **`DefensiveBase.reset()` on its own.** A bare `DefensiveBase()` after
   `start_cooldown()` and `update(0.5)` has `cooldown_time == pytest.approx(1.0)`. After
   `reset()`, `cooldown_time == 0.0`, `cooldown_ratio == 0.0` and `can_fire() is True`.
   Calling `reset()` a second time changes nothing.
6. [test] **Cooldown still works inside a game.** After a start, `handle_actions(FIRE)`
   twice in a row gives exactly 1 defense missile. Then 89 calls of `update(DT_DEFAULT)`
   (just under 1.5 s) followed by `handle_actions(FIRE)` still give 1. 2 more
   `update(DT_DEFAULT)` calls (91 in total, just over 1.5 s) followed by
   `handle_actions(FIRE)` give 2. Use the `main_game` fixture so no enemies spawn.
7. [test] **Pause does not reset the cooldown.** After a start and one `FIRE`, call
   `update(0.5)`. Then `handle_actions({"toggle_pause": True})` twice (pause, then resume)
   leaves `state == STATE_PLAYING` and
   `base.cooldown_time == pytest.approx(BASE_COOLDOWN_TIME - 0.5)`. An immediate
   `handle_actions(FIRE)` adds no missile.
8. [test] **SPACE and click in the same frame still don't fire.** On a start-screen game,
   `handle_actions({"start": True, **FIRE})` gives `state == STATE_PLAYING`,
   `defense_missiles == []` and `base.cooldown_time == 0.0`. The launcher is ready for the
   next click.
9. [test] **Through the real loop.** On a start-screen game, monkeypatch `utils.timer.time`
   with a fake clock that advances `1/60` s per `handle_events` call, as in
   `tests/test_game_states.py` criterion 12. Fake `handle_events` to return
   `[{"start": True}, FIRE, {"quit": True}]`. Run `start_game_loop()`. Afterwards
   `len(defense_missiles) == 1`.
10. [test] **Dead attribute gone.** `not hasattr(game, "base_cooldown")` on a fresh
    `MainGame`, and `"base_cooldown" not in inspect.getsource(systems.game_loop)`.
11. [test] All existing tests pass unchanged. The full suite passes with the README
    command, and the real `config.json` is byte-for-byte unchanged.
12. [visual] **Missile leaves at once.** From a start-screen game, run
    `handle_actions({"start": True})`, then `handle_actions(FIRE)`, then 10 frames of
    `update(DT_DEFAULT)` and `check_collisions()`, then `draw()`. A `COLOR_YELLOW` defense
    missile is visible between the launcher (top-left, near
    `(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)`) and `(400, 300)`, about 63 px along that line.
    The HUD reads `"SCORE: 0"`.

## Touch points
- `entities/base.py`: new `DefensiveBase.reset()`.
- `systems/game_loop.py`:
  - `MainGame.start_game()`: one `self.base.reset()` call.
  - `MainGame.__init__`: delete `self.base_cooldown = 0.0`.
- `tests/test_reset_cooldown.py` (new).
- `game/constants.py`: no new constants. The job uses the existing `BASE_COOLDOWN_TIME`,
  `LAUNCHER_X_OFFSET`, `LAUNCHER_Y_OFFSET`, `DT_DEFAULT` and the `STATE_*` names.

Expected diff: about 10 lines of game code and about 120 lines of tests. Parametrise
criterion 3, and share a helper that builds a start-screen game and a fake-clock loop
driver.

## Notes for reviewers
- **code:**
  - The reset belongs in `start_game()`, not in the `handle_actions()` start branch, so
    anything that starts a game (including the `main_game` fixture) gets a ready launcher.
  - `reset()` must mutate `self.base` in place. `draw()` and the tests hold a reference to it.
  - Nothing in the pause or resume branches may touch the base.
  - Criterion 6 checks 89 and 91 frames, not 90, because `90 * DT_DEFAULT` sits right on
    1.5 s and float drift makes that boundary unreliable.
- **security:** No new file, network or config I/O. Tests must patch `CONFIG_PATH` before
  building any `MainGame`, and the `utils.timer.time` monkeypatch must stay scoped to its
  test.
- **ux:**
  - The first click of every new game now fires at once. This includes a click made in the
    first frame after SPACE, which used to be swallowed for up to 1.5 s.
  - Holding the reload across pause is deliberate: ESC twice must not be a way to skip it.
  - SPACE plus a click in the same frame still won't fire. That is the existing rule, and a
    single frame is too short for a player to notice.
- **ui:** Nothing new is drawn. Check frame 12: the missile appears in the frames right
  after the click, and the launcher looks the same as before.
