STATUS: READY

## Round 1
**Summary** — Added `MainGame.get_shake_offset()`. It takes `A = math.ceil(shake_intensity)` and only then calls `random.randint(-A, A)`, so `random.randint` always gets int arguments. It returns `(0, 0)` when `shake_intensity <= 0`. `draw()` now calls it in place of the two crashing `randint` lines, and `shake_x`/`shake_y` are still unused (out of scope). The shake magic numbers 5, 8 and `* 2` are now `SCREEN_SHAKE_BUILDING_HIT`, `SCREEN_SHAKE_INTERCEPT` and `SCREEN_SHAKE_DECAY_RATE` in `game/constants.py`, with the same values. Also added `tests/conftest.py` (SDL dummy env vars set before any pygame import, repo root put at the front of `sys.path`, and a `main_game` fixture), `tests/test_screen_shake.py` (10 tests), and a "Running tests" section in `README.md`.

**Commits**
- `04dfbf0 001-fix-shake-crash: integer screen-shake offsets via get_shake_offset and shake constants`
- `69efe26 001-fix-shake-crash: add pytest harness, screen-shake regression tests, README test docs`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Building-hit regression, 10 frames, missile destroyed, shake == BUILDING_HIT right after the hit | `test_building_hit_does_not_crash_on_following_frames` | Yes |
| 2 | Float path exercised; fails on main with TypeError | Same test asserts `shake_intensity != int(shake_intensity)` after the frame-2 `update()`, then `draw()`. I ran it with the fix removed (constants present, old `game_loop.py`): it failed with `TypeError: 'float' object cannot be interpreted as an integer` at `game_loop.py:166` (the old `randint` line), raised from the test's frame-2 `draw()` (test line 62). Running the same script against a `git archive main` checkout also raised that TypeError on the frame after the hit. | Yes |
| 3 | `draw()` with 4.5 / 0.01 / INTERCEPT-0.25 | `test_draw_with_fractional_shake_intensity[4.5/0.01/7.75]` (all three failed with TypeError before the fix) | Yes |
| 4 | 200 calls at 4.97, seed 0: `type(v) is int`, in [-5, 5] | `test_get_shake_offset_returns_bounded_ints` | Yes |
| 5 | `(0, 0)` for 0 and 0.0 | `test_get_shake_offset_zero_when_no_shake[0/0.0]` | Yes |
| 6 | Decays to 0 after 160 frames, then draw OK | `test_shake_decays_to_zero_after_building_hit`. It passes before and after the fix, because decay behaviour is unchanged and draw at 0 never crashed. It guards behaviour rather than reproducing the bug. | Yes |
| 7 | Intercept sets INTERCEPT, next update + draw OK | `test_intercept_sets_shake_and_next_frame_draws` (failed with TypeError before the fix) | Yes |
| 8 | CONFIG_PATH under tmp_path; SDL_VIDEODRIVER dummy | `test_harness_isolates_config_and_display` | Yes |
| 9 | Suite passes headless with and without the env vars; config.json unmodified | Passed with the SDL vars. Also passed via `env -u SDL_VIDEODRIVER -u SDL_AUDIODRIVER uv run ... python -m pytest -q`, where conftest sets them. The system `python3` here has no pygame installed, so "plain `python -m pytest`" was tested through uv's interpreter without the env vars. `git status --short config.json` was empty after the runs. | Yes |
| 10 | Visual frame after hit unchanged | Rendered headless (fixture-equivalent setup, seed 0, hit, one more `update(DT_DEFAULT)`, `draw()`, shake 4.967) and viewed it: blue-gradient sky, white launcher top-left, gray buildings along the bottom, yellow `SCORE: 0` top-right. Also compared the hit frame (shake 5, which `main` can still render) between `main` and the branch: pixel-identical. `main` crashes on the next frame. | Yes |

Note on the fixture teardown: the `main_game` fixture runs `gc.collect()` at setup and again at teardown, then calls `pygame.quit()`. I checked that `MainGame` has no reference cycles: with gc disabled, plain refcounting freed it. So once pytest drops its reference, any stale game's `__del__` (`pygame.quit()`) runs before the next test's setup, not partway through a later test.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `10 passed in 0.63s`
