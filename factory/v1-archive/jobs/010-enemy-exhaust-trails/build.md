STATUS: READY

## Round 1
**Summary** — `IncomingMissile` now has a `trail` (a `deque(maxlen=ENEMY_TRAIL_MAX_POINTS)`, empty at birth). `update(dt)` saves a `Vector2` copy of the position *before* moving, but only when the missile is not destroyed and is at least `ENEMY_TRAIL_SPACING` px past the newest sample. The new `trail_segments()` returns head-to-tail `(start, end, color)` tuples, each colour a per-channel blend from `ENEMY_TRAIL_HEAD_COLOR` to `ENEMY_TRAIL_TAIL_COLOR` rounded to ints and clamped to 0–255. The new `draw_trail(screen)` draws them oldest first. `MainGame.draw()` has one new loop that draws every live enemy trail before the defense-missile loop. There are five new constants in a `# Enemy missile exhaust trail` block right after `# Missile speeds`, plus one new README Features bullet.

**Commits**
- `6b4b6a4 010-enemy-exhaust-trails: fading exhaust trails behind enemy missiles`
- `e7952fb 010-enemy-exhaust-trails: tests for trail sampling, segments, pixels and draw order`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_constants` | Yes |
| 2 | Empty at birth | `test_empty_at_birth` | Yes |
| 3 | Sampling (copies, before move) | `test_sampling_records_copies_before_moving` | Yes |
| 4 | Spacing | `test_spacing` | Yes |
| 5 | Cap | `test_cap` (also asserts len <= 12 after every step) | Yes |
| 6 | Same length at 30/60/144 fps | `test_length_independent_of_frame_rate[...]` x3 | Yes |
| 7 | Stopped when destroyed | `test_destroyed_missile_stops_recording` | Yes |
| 8 | Segments | `test_segments` | Yes |
| 9 | Pixels | `test_pixels` | Yes |
| 10 | Wired into game frame | `test_wired_into_game_frame` | Yes |
| 11 | Draw order | `test_draw_order` | Yes |
| 12 | Destroyed missiles draw no trail | `test_destroyed_missile_draws_no_trail` | Yes |
| 13 | Pause freezes, restart clears | `test_pause_freezes_and_restart_clears` | Yes |
| 14 | Real spawns | `test_real_spawns` | Yes |
| 15 | Scope fence | `test_scope_fence` (passes before and after: it is a fence) | Yes |
| 16 | Existing tests pass, config.json unchanged | Full suite 182 passed. No existing test file edited. `config.json` sha256 `bbf68775…caa4c` is the same before and after the run | Yes |
| 17 | [visual] Mid-flight frame | Rendered seed-1 frame (3 spawns, 90 frames). Each red head has a thin 2 px trail about 80 px long (measured distance from head to `trail[0]` = 80.0 for all three), along its line of flight toward the top. In a 6x zoom it is orange next to the head and steps down to grey at the tail. The heads sit on top of their trails. A pixel diff against the base commit's render of the same frame shows 423 changed pixels, all in x 140–675, y 160–238 (the trail area). The launcher, reload bar and HUD are pixel-identical. | Yes |
| 18 | [visual] Trail meets a shot | Spec frame (shot just below a head, plus 20 frames): the yellow dot is still near the launcher and does not cross a trail yet. The rest of the frame looks correct. To check overlap I rendered two more frames. (a) Shot at (200, 470), frame 61: the yellow dot sits on a trail and is drawn fully over it (centre pixel `COLOR_YELLOW`, 6x zoom checked). (b) A player explosion placed on a live trail 67 px behind its head: the explosion disc covers the trail and no trail pixels show through it. | Yes |

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `182 passed in 6.63s`. Before the implementation, the new file gave `16 failed, 1 passed` (the scope fence was the one that passed).

**Notes**
- The new test file is 317 lines, a bit over the 200–250 estimate. Most of the extra is docstrings and the per-channel monotonic check in criterion 8.
- `trail_segments()` returns fresh `Vector2` copies for start/end, so callers can't change the trail through it.
- Nothing outside the touch points changed. `DefenseMissile`, `entities/base.py`, the `LAUNCHER_*` constants and the README "Gameplay" paragraph are untouched.
