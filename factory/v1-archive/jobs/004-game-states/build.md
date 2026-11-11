STATUS: READY

## Round 1
**Summary** — `InputSystem` now sends `"toggle_pause"` for ESC and `"start"` for SPACE. The new `MainGame.handle_actions()` makes every input-driven state change. It picks the transition from the state at the start of the call, makes at most one change, calls `timer.reset()` every time the game enters `STATE_PLAYING`, and only fires if the game was playing both before and after. `start_game_loop()` no longer forces a game. It stops at once on `"quit"` and otherwise calls `handle_actions()` and then runs the playing frame or the menu. The old SPACE branch that removed buildings, the `"resume"` and `"pause"` branches and the inline restart block are all deleted. Spawns now use `game_time`, and `start_game()` sets `last_spawn_time = 0.0` and `shake_intensity = 0`. `draw_start_screen()` draws the new `menu_lines()` centred for START and PAUSED, and the README controls table is updated.

**Commits**
- `f7694ae 004-game-states: handle_actions owns input transitions, loop opens on start screen, game-time spawns, centred menu lines`
- `8360967 004-game-states: tests for key mapping, start/pause/restart transitions, game-time spawns and menu text`

Diff against `b78281e`: 308 insertions and 90 deletions across 4 files. That is 77 game-code insertions and 84 deletions in `game_loop.py`, 2/2 in `input_system.py`, 4/4 in the README and 231 test lines. The test file is a little over the ~200 target, but the total stays under 400.

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| 1 | Key mapping | `test_input_mapping[ESC/SPACE/click]` | yes |
| 2 | Opens on start screen | `test_opens_on_start_screen` (real loop, fake quits on call 5, asserts 5 calls) | yes |
| 3 | SPACE starts play | `test_space_starts_play` | yes |
| 4 | Start screen ignores other input | `test_ignored_input[start-*]` (fresh game) | yes |
| 5 | ESC pauses and resumes without loss | `test_pause_and_resume_keep_everything` | yes |
| 6 | Paused input ignored | `test_ignored_input[paused-*]` | yes |
| 7 | SPACE during play does nothing | `test_ignored_input[playing-actions4]` (same objects, same order) | yes |
| 8 | Firing works in play; ESC+click pauses without firing | `test_firing_in_play` | yes |
| 9 | SPACE restarts from game over, no second save | `test_space_restarts_from_game_over` | yes |
| 10 | ESC on game over does nothing | `test_ignored_input[game_over-actions5]` | yes |
| 11 | Spawns on game time, no `get_ticks` | `test_spawns_run_on_game_time` (0 at 180 frames, 1 at 210, first spawn ≈3.32 s) | yes |
| 12 | Pause doesn't advance game time or cause a burst of spawns | `test_pause_does_not_advance_game_time` (real loop, 41 calls, game_time = 37/60) | yes |
| 13 | Menu text and layout; all three screens draw | `test_menu_text` | yes |
| 14 | Existing tests pass unchanged; real config.json untouched | Full suite 73 passed, including 003's `test_real_loop_ends_game_and_saves_once`; `config.json` md5 `3fa9655f…` same before and after | yes |
| 15 | [visual] Start screen | Frame checked: title (white), subtitle (gray, dim but readable), "High Score: 250" (yellow), four white control lines, "Press SPACE to Start" (48 pt yellow). All centred, none overlapping | yes |
| 16 | [visual] Pause screen | Frame checked: "PAUSED", "Score: 1,234" (yellow), four control lines, "Press ESC to Resume" (yellow). All centred, none overlapping | yes |
| 17 | [visual] First playing frame | Frame checked: 8 gray buildings along the bottom, launcher top-left, "SCORE: 0" top-right, no missiles | yes |

The new tests were run against the original code (stashed): 16 failed and 1 passed. The left-click case of criterion 1 passes on both because that mapping didn't change.

Other notes:
- `get_ticks` is now used only in the dead `handle_score_updates()`.
- The old `"pause"`, `"start_pause"` and `"resume"` strings are gone.
- `self.state = STATE_PLAYING` appears only in `handle_actions()`.
- The loop no longer resets `total_missile_hits_this_level`. That field is used only by the dead `handle_score_updates()`.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `73 passed in 3.47s`
