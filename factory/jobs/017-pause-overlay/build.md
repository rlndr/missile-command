STATUS: READY

## Round 1
**Summary** — `draw()`'s body moved unchanged into a new read-only `draw_scene()`. `draw()` is now `draw_scene()` + `flip()`, and play frames are pixel-identical to HEAD (checked by rendering the same seeded frame with both trees). The `STATE_PAUSED` branch of `draw_start_screen()` now draws the scene, then `draw_pause_overlay()` (a cached `SRCALPHA` surface built in `__init__` from the new `PAUSE_OVERLAY_COLOR`/`PAUSE_OVERLAY_ALPHA` constants), then the menu text, then one flip. Start and game over screens are unchanged. `menu_lines()` returns the pause screen's own six-row list (ESC: Resume, M mute line kept at `mid + 140`). The start list is unchanged. README has one new paragraph at the end of Gameplay.

**Commits**
- `2784227 017-pause-overlay: pause dims the frozen battlefield and lists only ESC and M`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_pause_overlay.py::test_constants` (import error before change) | Yes |
| 2 | Pause dims the live scene | `test_pause_dims_live_scene` (failed before: flat fill) | Yes |
| 3 | Text on top of overlay | `test_text_on_top_of_overlay`. Already passed on the old flat screen, so I mutation-checked it: with the overlay drawn after the text, it fails | Yes |
| 4 | Exact pause lines | `test_exact_pause_lines` (failed before) | Yes |
| 5 | No dead controls; start list unchanged | `test_no_dead_controls` (failed before: SPACE line) | Yes |
| 6 | ESC/M work while paused, end to end | `test_listed_keys_work_while_paused` (regression guard; input code untouched, so it passed before too) | Yes |
| 7 | Pausing and drawing change nothing | `test_pausing_and_drawing_change_nothing` (regression guard; the parked missile gets two trail points so the trail check means something) | Yes |
| 8 | One flip per frame | `test_one_flip_per_frame` (failed before: no `draw_scene`) | Yes |
| 9 | Start / game over don't show scene | `test_start_and_game_over_hide_scene[start]`, `[game_over]` (regression guard) | Yes |
| 10 | Pause through the real loop | `test_pause_through_real_loop`: scene 11, menu 6, ends paused (failed before) | Yes |
| 11 | Existing tests pass unedited; config.json unchanged | Full suite 388 passed; `config.json` md5 `ecaa6552…` same before and after | Yes |
| 12 | [visual] Paused mid-fight | Frame `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/017-builder/frame12.png`: dimmed sky, city, grey tower, reload bar, enemy missile and trail, HUD. Crisp white PAUSED / Controls: / ESC: Resume / M: Mute sound and yellow Score: 4 / Press ESC to Resume. No SPACE or mouse line | Yes |
| 13 | [visual] Paused in rapid fire, muted | Frame `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/017-builder/frame13.png`: dimmed tower is clearly dark red, and "M: Unmute sound" is in the same row | Yes |

Render script: `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/017-builder/render.py` (args: repo root, output png, `play`/`pause`/`rapid`).

UI note for reviewers: as the spec predicts, there is a wide gap between "Score:" (`mid - 30`) and "Controls:" (`mid + 80`). In the rendered frames the gap reads as two groups (status, then controls) and does not look broken. The dimmed HUD score at the top right sits clearly behind the overlay, so it reads as part of the frozen scene and not as a duplicate.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `388 passed in 20.49s`
