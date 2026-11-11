STATUS: READY

## Round 1
**Summary** — Added `DefensiveBase.reload_progress()`, which works from `cooldown_time` and `is_active` (never `cooldown_ratio`), clamps to [0, 1] and returns 0.0 when the launcher is offline. Added `DefensiveBase.cooldown_bar_rects()`, which builds the track from `get_bounds()` and `self.width` and rounds the fill width down with `int()`. `draw_base()` now draws the track and then the fill (yellow when `can_fire()`, orange otherwise, nothing when the width is 0), with its signature unchanged. Added five `COOLDOWN_BAR_*` constants under "Defensive base settings" after the `COLOR_*` names, and one README Gameplay sentence. `systems/game_loop.py` and the existing tests are untouched.

**Commits**
- `b66fe3d 008-cooldown-indicator: draw a reload bar under the launcher`
- `077173c 008-cooldown-indicator: tests for reload progress, bar geometry, pixels and game wiring`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_constants` | Yes |
| 2 | Bar position | `test_bar_position` | Yes |
| 3 | `reload_progress()` values | `test_reload_progress_values`. The offline case fails if the `is_active` guard is removed (checked by mutation). | Yes |
| 4 | Clamped, full only when ready | `test_progress_clamped_and_full_only_when_ready[-1.0, 0.0, 0.001, 0.75, 1.5, 3.0]`. The 0.001 case fails if `int()` is swapped for `round()` (checked by mutation). | Yes |
| 5 | Fill widths | `test_fill_widths` | Yes |
| 6 | Pixels: ready | `test_pixels_ready` | Yes |
| 7 | Pixels: just fired | `test_pixels_just_fired` | Yes |
| 8 | Pixels: half reloaded | `test_pixels_half_reloaded` | Yes |
| 9 | Fills over a real reload | `test_fills_over_real_reload` (never shrinks, full iff `can_fire()`, frame 89 < 60, frame 91 == 60). Also fails under the `round()` mutation. | Yes |
| 10 | Wired into the game frame | `test_wired_into_game_frame` | Yes |
| 11 | Pause freezes the bar | `test_pause_freezes_bar` | Yes |
| 12 | New game shows a full bar | `test_new_game_shows_full_bar` | Yes |
| 13 | Not on menu screens | `test_not_on_menu_screens`. This guards against a regression: it passes on `main` once the constants exist, because the menu screens never drew the launcher. | Yes |
| 14 | Existing tests pass, config.json unchanged | Full suite: 165 passed. No existing test file was edited. The sha256 of `config.json` was `bbf68775…c4a` before and after. | Yes |
| 15 | [visual] Mid-reload frame | Rendered a headless frame after FIRE and 45 frames, then zoomed in on the top-left. A thin bar the launcher's width sits under the white launcher with a 4 px gap. The left half is orange and the right half dark blue, and it stands out against the blue sky. The yellow missile is in flight and the HUD shows `SCORE: 0`. The fill is 29 px, not 30, because 45 summed `DT_DEFAULT` steps leave a little over 0.75 s, and `int()` rounds that down. | Yes |
| 16 | [visual] Ready frame | Rendered the same game 60 frames later. The whole bar is the same yellow as the defense missile and the HUD text. The launcher body and tube are unchanged. The HUD reads `SCORE: 1` from 1.75 s of survival, and the explosion at (400, 300) is far from the launcher. | Yes |

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `165 passed in 6.11s`. Before the change, all 18 new tests failed (missing constants/methods).

Note: the test file is 272 lines, a bit over the 150–200 estimate. It has one test per criterion plus shared `_px`, `_region`, `_surface_draw` and `_fill_width` helpers, and a `start_screen_game` fixture that patches `CONFIG_PATH` before building `MainGame()`.
