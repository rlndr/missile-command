STATUS: READY

## Round 1
**Summary** — Added `MainGame.current_spawn_interval()` straight after `spawn_incoming_missile()`. It floors the existing ramp at `MIN_SPAWN_INTERVAL`, then divides by the new `RAPID_FIRE_SPAWN_RATE_MULTIPLIER` (2) whenever `self.rapid_fire_active()` is true, which gives 1.0 s during the 60–70 s window. `update()` now calls it in place of the inline two-line `max(...)`, and the spawn test, the single spawn call and `last_spawn_time` handling are unchanged. Also added one README Features bullet and a new test file. `rapid_fire_active()`, the Gameplay paragraph, `entities/` and `systems/sound.py` are not touched.

**Commits**
- `53fc906 016-rapid-fire-double-spawn: double the enemy spawn rate while rapid fire is on`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constant = 2; base/min unchanged | `test_spawn_rate_multiplier_constant` | Yes |
| 2 | Interval values outside/inside window | `test_interval_outside_window_is_the_normal_ramp` (0, 30, 45, 59.99, 70, 100), `test_interval_inside_window_is_halved_after_floor` (60, 65, 69.99) | Yes |
| 3 | Window state read only via `rapid_fire_active()` | `test_interval_multiplier_applies_to_ramped_value`, `test_interval_ignores_game_time_when_rapid_fire_forced_off`, `test_interval_follows_repeating_window_rule` (015 rule: 1.0 at 125/185, 2.0 at 100/130), plus `test_interval_code_has_no_window_time_logic` (source has no `RAPID_FIRE_START_TIME`/`RAPID_FIRE_DURATION`) | Yes |
| 4 | 10 spawns in window vs 5 outside | `test_window_gets_twice_as_many_spawns` | Yes |
| 5 | Entering: `[60.0, 61.0, 62.0]` | `test_first_window_frame_spawns_after_one_second` | Yes |
| 6 | Leaving: `[71.0]` | `test_leaving_window_returns_to_normal_interval` | Yes |
| 7 | One missile per spawn / per frame | `test_real_spawns_make_one_missile_each` (2 then 1), `test_huge_dt_spawns_at_most_once` | Yes |
| 8 | Pause freezes doubled rate | `test_pause_freezes_doubled_rate` | Yes |
| 9 | New game resets | `test_new_game_resets_spawn_interval` | Yes |
| 10 | Launcher behaviour unchanged | `test_launcher_rapid_fire_follows_window` | Yes |
| 11 | Nothing else changed | Full suite 363 passed with no existing test edited (includes `test_game_states.py::test_spawns_run_on_game_time` and all of `test_rapid_fire.py`); `test_real_config_untouched`, and `sha256sum config.json` is `e39479a1…ed8` before and after; `git diff HEAD~1 -- entities systems/sound.py` is empty; the `game_loop.py` hunks are only at the new method (after line 126) and the `update()` interval lines, with nothing inside `rapid_fire_active()` | Yes |
| 12 | [visual] Busier window | Rendered headless with `random.seed(0)`, 0.25 s steps plus `check_collisions()`: `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/016-builder/window.png` (59.75→66.0) has a red tower and 3 red enemy heads with orange-to-grey trails, plus an impact explosion on the left of the city. `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/016-builder/normal.png` (89.75→96.0) has a white tower and 2 heads. The HUD layout, city and reload bar are the same in both. The wave number differs (3 vs 4) only because `game_time` differs. | Yes (see note) |

Note on 12: the difference on screen is 3 heads against 2, not a dramatic one. A missile takes about 2.75 s to fall, so on average about 2.75 are in the air at a 1.0 s interval and about 1.4 at 2.0 s. The spawn count doubles (6 against 3 over the same span), but what shows in a single frame is capped by fall time. This is a ux point for play-testing, not a defect against the spec.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `363 passed in 17.72s`.
Before the change, `tests/test_rapid_fire_spawns.py` gave `19 failed, 4 passed`. The 4 that passed are regression guards that hold either way: leaving the window (`[71.0]`), huge `dt` spawning once, the launcher flag, and the real config.
