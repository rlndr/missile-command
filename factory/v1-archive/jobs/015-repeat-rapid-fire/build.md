STATUS: READY

## Round 1
**Summary** — `MainGame.rapid_fire_active()` now returns `False` before `RAPID_FIRE_START_TIME`, and otherwise `(game_time - RAPID_FIRE_START_TIME) % RAPID_FIRE_INTERVAL < RAPID_FIRE_DURATION`. That gives windows at [60, 70), [120, 130), ... worked out from `game_time` only. I updated its docstring and made no other line change in `game_loop.py`. I added `RAPID_FIRE_INTERVAL = 60.0` to the rapid-fire block in `game/constants.py` and reworded that block's heading comment, and rewrote the one README Gameplay sentence. `entities/base.py`, `systems/sound.py` and `config.json` are untouched. The new tests are in `tests/test_repeat_rapid_fire.py`, and no existing test was edited.

**Commits**
- `7244d7b 015-repeat-rapid-fire: rapid-fire window repeats every 60 s of play`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| 1 | Constants | `test_constants` (fails before the change: ImportError on `RAPID_FIRE_INTERVAL`) | Yes |
| 2 | Window boundaries across several minutes | `test_window_open[*]` (9 cases), `test_window_closed[*]` (11 cases). All `test_window_open` cases from 120 s on failed before the change. With the `< RAPID_FIRE_START_TIME` guard removed, `test_window_closed[0.0/5.0/9.99]` fail, so the guard is covered | Yes |
| 3 | Exactly one on/off pair per minute | `test_one_on_off_pair_per_minute` (2000 × `update(0.1)`: 3 ons, 3 offs within 0.11 s of the edges, 297–303 on frames) | Yes |
| 4 | Fast reload in 2nd and 3rd windows | `test_fast_reload_in_later_windows[120.1]`, `[180.1]` | Yes |
| 5 | Normal reload between windows | `test_normal_reload_between_windows[100.0]`, `[150.0]` (guard test: passes before and after) | Yes |
| 6 | New window cuts a running slow reload | `test_new_window_cuts_slow_reload` | Yes |
| 7 | Short reload finishes after 2nd window | `test_short_reload_finishes_after_second_window` | Yes |
| 8 | Sound follows each window | `test_sound_follows_each_window` (launch at 10/100/150, laser at 65/125/185, one call each) | Yes |
| 9 | Pause freezes a later window | `test_pause_freezes_later_window` | Yes |
| 10 | New game restarts the cycle | `test_new_game_restarts_cycle` | Yes |
| 11 | Tower colour in rendered frames | `test_frame_tower_colour[*]` (red at 125/185, white at 100/135, body and barrel) | Yes |
| 12 | Long game, no audio, no crash | `test_second_window_no_audio_no_crash` (from 119.5 s, 120 frames of fire/update/collide/draw) | Yes |
| 13 | Nothing else changed | Full suite 377 passed with no edits to existing tests. `test_real_config_untouched` (new file). `git diff --stat main` shows only README.md, game/constants.py, systems/game_loop.py and the new test file | Yes |
| 14 | [visual] Red tower in 2nd window | Frame at game_time ≈125.05 reached via `update()`, with 3 defence missiles in flight. Tower body and barrel are solid red, the reload bar is in place under the tower (full, yellow) and the HUD reads `WAVE: 5  SCORE: 0` | Yes |
| 15 | [visual] White between windows | Frame at ≈135.05 has a white tower and an orange reload sliver, and the HUD reads `WAVE: 5`. It looks the same as the ≈10.05 frame (which reads `WAVE: 1`) | Yes |

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `377 passed in 19.16s`

Notes:
- The new test file is about 300 lines, more than the spec's 150–200 estimate. Each criterion has its own parametrised test and helpers are copied rather than imported, as the spec allows.
- Render script and frames: `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/015-builder/` (`render.py`, `t125.png`, `t135.png`, `t010.png`).
