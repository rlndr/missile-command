STATUS: READY

## Round 1
**Summary** — Added `DefensiveBase.reset()` (`entities/base.py`). It sets `cooldown_time = 0.0`, `cooldown_ratio = 0.0` and `is_active = True`, and leaves position, size and render offsets alone. `MainGame.start_game()` now calls `self.base.reset()` on the existing launcher, which covers SPACE from both START and GAME_OVER, plus the `main_game` fixture. Deleted the dead `self.base_cooldown = 0.0`. The pause/resume branches don't touch the base. New tests are in `tests/test_reset_cooldown.py`; no existing test files were edited.

**Commits**
- `b4df90d 007-reset-cooldown: add DefensiveBase.reset(), call it from start_game(), drop dead base_cooldown`
- `da6c7c2 007-reset-cooldown: tests for a ready launcher on start, restart, pause and the real loop`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| 1 | First click of the first game fires | `test_first_click_of_first_game_fires` (fails before the fix) | Yes |
| 2 | First click after a restart fires | `test_first_click_after_restart_fires` (fails before the fix) | Yes |
| 3 | Every way into a game resets it | `test_every_way_into_a_game_resets` with 6 parametrised cases (START/GAME_OVER × 0.01/0.75/1.5); all fail before the fix | Yes |
| 4 | Same launcher object | `test_start_game_keeps_the_same_launcher`. This is a guard test, so it also passes before the fix; it would fail if `start_game()` built a new base | Yes |
| 5 | `DefensiveBase.reset()` on its own, idempotent | `test_base_reset_on_its_own` (AttributeError before the fix) | Yes |
| 6 | Cooldown still works in a game (89 / 91 frames) | `test_cooldown_still_works_in_a_game` (fails before the fix). See the note below | Yes |
| 7 | Pause does not reset the cooldown | `test_pause_does_not_reset_the_cooldown` | Yes |
| 8 | SPACE + click in the same frame don't fire, but the launcher is ready | `test_space_and_click_same_frame_do_not_fire` | Yes |
| 9 | Through the real loop with a fake clock | `test_first_click_through_the_real_loop` (`utils.timer.time` monkeypatched only inside this test) | Yes |
| 10 | Dead attribute gone | `test_dead_base_cooldown_attribute_gone` | Yes |
| 11 | Existing tests pass unchanged; real `config.json` unchanged | Full suite: 147 passed. `sha256sum config.json` gave `bbf68775…caa4c` both before and after | Yes |
| 12 | [visual] Missile leaves at once | Rendered headless: START, FIRE, 10 × (`update(DT_DEFAULT)` + `check_collisions()`), `draw()`. Yellow missile at (71.0, 57.6), which is 63.3 px from (20, 20) along the line to (400, 300). The pixel there is `(255,255,50)` = `COLOR_YELLOW`. HUD reads `SCORE: 0`. The launcher looks the same as before | Yes |

**Note on criterion 6:** the spec says to check `len(defense_missiles)`. Taken literally, that can't work. The first missile flies about 472 px at 380 px/s, so it reaches (400, 300) after about 1.24 s, detonates, and is filtered out of the list before frame 89 (1.48 s). The live list would then hold 0, not 1. So the test counts launches instead: it patches `systems.game_loop.DefenseMissile` with a subclass that records every launch. That gives exactly 1 launch after the double FIRE, still 1 after 89 frames + FIRE, and 2 after 91 frames + FIRE. It also checks `len(defense_missiles) == 1` right after the double FIRE, and that the newest live missile is the second recorded launch. The intent (no fire before 1.5 s, fire after) is tested as written.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `147 passed in 5.88s`. With only the new test file and no fix: `14 failed, 1 passed` (the 1 is criterion 4's guard test).
