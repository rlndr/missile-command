STATUS: READY

## Round 1
**Summary** — The launcher is now a white tower (60x50 body plus an 8x16 barrel, same colour) standing on a new `COLOR_GROUND` strip at the bottom centre. `DefensiveBase.position` is the muzzle `(LAUNCHER_X, LAUNCHER_Y)` = (400, 514), and `DefenseMissile` starts from the same constants. `start_game()` builds the city as two mirrored groups of four (x 30–330 and 470–770) from `CITY_EDGE_MARGIN`, `BUILDING_SPACING` and the building width, with y = `GROUND_Y - height`. `LAUNCHER_X_OFFSET`/`LAUNCHER_Y_OFFSET` are gone with no alias. README and GAME_DESIGN §4.1, §4.2, §10 and §13 are updated. `reload_progress()` and `cooldown_bar_rects()` are untouched; the bar moved only because `get_bounds()` moved.

**Commits**
- `3d6b607 009-bottom-launcher: launcher tower on a ground strip at the bottom centre, city in two mirrored halves`
- `52b93fc 009-bottom-launcher: tests for the bottom tower, ground, city layout and rising missiles`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| 1 | Constants | `tests/test_bottom_launcher.py::test_constants` | Yes |
| 2 | Tower geometry | `test_tower_geometry` | Yes |
| 3 | Reload bar in ground strip | `test_reload_bar_in_ground_strip` | Yes |
| 4 | City layout | `test_city_layout` (positions, y, ground, no overlap, 40 px gap, mirror, second `start_game()`) | Yes |
| 5 | Missiles start at muzzle | `test_missiles_start_at_muzzle` | Yes |
| 6 | Missiles rise toward targets | `test_missiles_rise_toward_targets[target0..4]` (parametrised) | Yes |
| 7 | Flight time 33/34 | `test_flight_time` | Yes |
| 8 | Tower pixels (bare surface) | `test_tower_pixels` | Yes |
| 9 | Ground and tower in game frame | `test_ground_and_tower_in_game_frame` | Yes |
| 10 | Bar in game frame | `test_bar_works_in_game_frame` | Yes |
| 11 | Rising missile drawn | `test_rising_missile_drawn_above_tower` | Yes |
| 12 | Not on menu screens | `test_not_on_menu_screens` | Yes |
| 13 | No top-left leftovers | `test_no_top_left_leftovers` | Yes |
| 14 | Existing tests edited only per table; suite passes; config.json unchanged | Diff of `test_missiles_explode.py`, `test_reset_cooldown.py`, `test_cooldown_indicator.py`, `test_buildings_game_over.py` is limited to the table rows (`test_arrival_on_step_75_and_stays` renamed `..._step_34_...`). In `test_cooldown_indicator.py` every `(10, ROW)`/`(50, ROW)` game-frame sample became `(375, ROW)`/`(415, ROW)`, including the ones in criteria 12 and 13 there. Full suite 182 passed. `config.json` sha256 `bbf68775…caa4c` before and after. | Yes |
| 15 | [visual] Opening frame | Rendered headless with `random.seed(0)`. Olive strip along the bottom 20 px, white tower at the centre with a thin barrel above the rooftops, 4 grey buildings each side with clear sky between them and the tower, full yellow bar in the ground under the tower, score at top right, nothing in the top-left. | Yes |
| 16 | [visual] Firing frame | Fired at (150, 120), then 20 updates plus collisions. Missile at (332.1, 407.0), which is on the muzzle-to-target line (up and to the left). Bar is orange 13 px from the left with the rest dark blue. In a 4x zoom the dark-blue track reads clearly as a darker band on the olive ground. | Yes |

Before the change, all 17 new tests failed. `test_not_on_menu_screens` failed only because `COLOR_GROUND` was missing, since the start screen never drew the old tower there either.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `182 passed in 6.65s`

**Notes for reviewers**
- For the right-hand group, `start_game()` uses `(starting_buildings_count - 1 - i)` with i = 4..7, which equals the spec's `(3 - i)` with i = 0..3. There is still one `random.choice` per building in the same order, so seeded layouts and types are unchanged.
- UI: the `COLOR_DARK_BLUE` track (30, 40, 60) on the `COLOR_GROUND` (70, 90, 50) is darker than the ground and easy to see in the rendered frame. I didn't change `COLOR_GROUND`.
