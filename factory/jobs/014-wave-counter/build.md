STATUS: READY

## Round 1
**Summary** — Added `MainGame.current_wave()` (`int(self.game_time // WAVE_DURATION) + 1`; there is no new attribute or timer) and `hud_wave_text()`. I moved the HUD score lines out of `draw()` into a new `draw_hud()`. It draws the score exactly as before and puts the white wave text `HUD_WAVE_GAP` px to the left of the measured score rect, then returns `(score_rect, wave_rect)`. I added the three constants to the `# Scoring` section and one README Features bullet. `update()`, `start_game()`, `spawn_defense_missile()`, `entities/base.py` and `systems/sound.py` are not touched.

**Commits**
- `c1ff05f 014-wave-counter: wave number derived from game_time, shown in the HUD left of the score`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_constants` | Yes |
| 2 | Wave boundaries, `int` type | `test_wave_boundaries` (7 parametrised cases) | Yes |
| 3 | Wave goes up through play | `test_wave_goes_up_through_play` | Yes |
| 4 | HUD text | `test_hud_wave_text` | Yes |
| 5 | No wave bonus / side effects, no `wave` attr | `test_no_wave_bonus_or_side_effects` | Yes |
| 6 | Pause and game over freeze the wave | `test_pause_and_menus_freeze_wave` (local copy of fake-clock helper) | Yes |
| 7 | Restart goes back to wave 1 | `test_restart_goes_back_to_wave_one` | Yes |
| 8 | HUD layout, incl. max score / wave 1,001 | `test_hud_layout` | Yes |
| 9 | HUD pixels (white wave, clean gap, yellow-only score) | `test_hud_pixels` | Yes |
| 10 | HUD follows the wave, score rect fixed | `test_hud_follows_wave` | Yes |
| 11 | Wave moves left with the score | `test_wave_moves_left_with_score` | Yes |
| 12 | Existing tests unedited and passing; config.json unchanged | Full suite 308 passed; `test_scoring.py` untouched; `sha256sum -c` on `config.json` before/after: OK | Yes |
| 13 | [visual] Mid-play HUD | `frame13.png`: game_time 65.0, score 65. Top right shows `WAVE: 3` in white, a gap, then `SCORE: 65` in yellow, on the same row with the same font; the score sits 10 px from the top and right edges. White is legible on the blue top of the sky. | Yes |
| 14 | [visual] Long values | `frame14.png`: `WAVE: 1,001` and `SCORE: 123,456,789` on one row with no overlap or clipping (score rect x 554–790, wave rect x 385–530) | Yes |

All 17 new tests failed before the implementation (AttributeError: no constants or methods yet).

Frames: `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/014-builder/frame13.png`, `frame13_crop.png`, `frame14.png`, `frame14_crop.png` (render script `render.py` in the same folder).

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `308 passed in 14.39s`

**UX note** — The wave is only a progress marker for now. The change from N to N+1 is silent, and the HUD number is the only cue. Tying the spawn rate to the wave, or adding a banner or sound, is a possible follow-up.
