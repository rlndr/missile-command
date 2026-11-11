STATUS: READY

## Round 1
**Summary** — In `check_collisions()`, the `incoming.destroy()` branch for player explosions now calls `add_missile_hit(MISSILE_INTERCEPT_POINTS)`. It runs after the existing `is_destroyed` guard, so each missile scores once. `add_survival_time(dt)` now keeps a float `time_survived` and awards only the whole seconds crossed. It ignores `dt <= 0`, and `__init__`/`reset()` set it to `0.0`. The HUD text now comes from the new `hud_score_text()` and is blitted at `get_rect(topright=(SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN))`. `handle_score_updates()` and `total_missile_hits_this_level` are deleted. Added a `# Scoring` constants section, one README Gameplay sentence, and `tests/test_scoring.py` (19 tests).

**Commits**
- `3a5c827 006-scoring: award intercept points, accumulate survival seconds, right-align live HUD score; drop dead handle_score_updates`
- `4fc3e6a 006-scoring: tests for intercept points, survival accrual, restart, high score and HUD`
- `fd40551 006-scoring: tighten scoring tests and parametrise criteria 4, 5 and 9`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | One intercept scores once | `test_one_intercept_scores_once` | yes |
| 2 | Several intercepts in one blast | `test_several_intercepts_in_one_blast` | yes |
| 3 | Overlapping blasts don't double-count | `test_overlapping_blasts_count_once` | yes |
| 4 | No points for other deaths | `test_no_points_for_other_deaths[...]` ×4 (non-player blast, building impact → health 66, impact inside player blast → health 66, off-screen → gone) | yes |
| 5 | Survival accumulates across frames | `test_survival_accumulates_across_frames[59-0]` (59→0, 61→1) and `[3599-59]` (3599→59, 3601→60); `time_survived` approx n·DT checked at each step | yes |
| 6 | Large/uneven dt exact | `test_survival_large_and_uneven_dt` | yes |
| 7 | Non-positive dt ignored | `test_survival_ignores_non_positive_dt` | yes |
| 8 | Survival through the game | `test_survival_through_the_game` (121 frames → 2 == int(game_time)) | yes |
| 9 | Paused / game-over don't score | `test_menu_states_do_not_score[paused-0]`, `[game_over-50]`: fake `utils.timer.time` via monkeypatch, 10 × 1.0 s frames, then quit | yes |
| 10 | Restart resets scoring | `test_restart_resets_scoring` | yes |
| 11 | High score includes new points | `test_high_score_includes_new_points` (tmp config == `{"high_score": 12}`) | yes |
| 12 | HUD text is live | `test_hud_text_is_live` (text values plus pixel diff in `(SCREEN_WIDTH-300, 0, 300, 50)`) | yes |
| 13 | HUD on screen and right-aligned | `test_hud_right_aligned_and_on_screen` (score `HIGH_SCORE_MAX`: yellow pixel present, right 10 px margin red == `COLOR_BLUE[0]`) | yes |
| 14 | Dead code gone | `test_dead_score_code_removed` | yes |
| 15 | Existing tests pass; real config.json unchanged | Full suite 132 passed. `config.json` sha256 `bbf68775…caa4c` before and after, and `git status` is clean | yes |
| 16 | Mid-play HUD frame | Rendered headless (intercept, 61 frames with `check_collisions()`, `draw()`). Shows "SCORE: 11" in yellow top-right, text rect `(667, 10, 123, 24)`: right edge 790 (10 px margin), top 10. No overlap with the launcher at top-left. The blast had already expired by frame 61 (0.25 + 61/60 s > 0.8 s life), so it isn't in this frame | yes |
| 17 | Large score frame | Rendered with score 123456789. Shows "SCORE: 123,456,789" fully visible, rect `(554, 10, 236, 24)`, no clipping at the right edge, legible over the light top of the sky | yes |

Pre-change check: I ran `tests/test_scoring.py` against the pre-change `systems/` (new constants present). 13 failed, and the other 6 passed: the 4 cases of criterion 4 and the 2 of criterion 9. Those 6 assert that *no* points are awarded, which the old code also satisfied, so they act as regression guards. Criterion 10 includes a precondition (`score == 10` before restart), so it fails on the old code.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `132 passed in 4.96s`

Notes: the total diff is 302 insertions and 25 deletions. Game code is about 30 lines net and tests are 273 lines, slightly over the "under 300" estimate in the spec. The tests use the shared helpers `_park`, `_blast`, `_loop_with_fake_clock` and `_region`, and parametrise criteria 4, 5 and 9. The unused `ScoreDisplay` class and `add_building_destroyed()` are untouched, as the spec requires.
