STATUS: READY

## Round 1
**Summary** — Updated `CollisionSystem.building_in_explosion` to measure distance from the explosion centre to the nearest point on `building.get_bounds()`, matching `building_to_explosion`. Added building explosion constants (`BUILDING_EXPLOSION_MAX_RADIUS = 110`, `BUILDING_EXPLOSION_EXPANSION_TIME = 0.4`, `BUILDING_EXPLOSION_SHRINK_TIME = 0.5`, `BUILDING_EXPLOSION_LAYERS`, `BUILDING_EXPLOSION_FLICKER_SPEED`, `BUILDING_EXPLOSION_FLICKER_AMOUNT`) and implemented `is_building` support, `fade_alpha()`, `fire_layers()`, translucent `SRCALPHA` rendering, and pool reset on `Explosion` and `ExplosionPool`. Updated `MainGame.check_collisions` to apply `building.take_impact()` first and spawn a `is_building=True` fireball at the building's centre on fatal hits while keeping non-fatal hits at the missile contact point.

**Commits** — `27026ff 018-building-explosions: fix building_in_explosion and play fiery explosion on building destruction`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants defined with required values | `tests/test_building_explosions.py::test_building_explosion_constants` | Yes |
| 2 | `CollisionSystem.building_in_explosion` measures from nearest point on building rect | `tests/test_building_explosions.py::test_building_in_explosion_uses_nearest_point` | Yes |
| 3 | Building explosion timeline and peak size (`0.4` s expand to `110`, `0.5` s shrink/fade) | `tests/test_building_explosions.py::test_building_explosion_timeline` | Yes |
| 4 | Layered red/orange/yellow fire and deterministic flicker | `tests/test_building_explosions.py::test_fire_layers_and_deterministic_flicker` | Yes |
| 5 | Rendered fire layers and fading on a surface | `tests/test_building_explosions.py::test_rendered_fire_layers_and_fade` | Yes |
| 6 | Pool reuse resets `is_building` and timing fields | `tests/test_building_explosions.py::test_pool_reuse_resets_building_explosion_fields` | Yes |
| 7 | Non-fatal vs fatal building hits in `MainGame.check_collisions()` | `tests/test_building_explosions.py::test_non_fatal_vs_fatal_building_hits` | Yes |
| 8 | Building explosion does not intercept missiles or harm adjacent buildings | `tests/test_building_explosions.py::test_building_explosion_harmless_to_missiles_and_adjacent_buildings` | Yes |
| 9 | In-game rendering of a destroyed building's fireball | `tests/test_building_explosions.py::test_in_game_rendering_of_destroyed_building_fireball` | Yes |
| 10 | All existing tests pass unchanged | Full pytest suite (`433 passed`) | Yes |
| 11 | [visual] Peak building fireball vs defense blast | Checked `018_criterion11_peak.png` (`t = 0.4` s) | Yes |
| 12 | [visual] Fading fireball | Checked `018_criterion12_fade.png` (`t = 0.7` s) | Yes |

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3.13 -m pytest -q` -> `433 passed, 1 warning in 23.04s`.
