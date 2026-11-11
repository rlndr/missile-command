STATUS: READY

## Round 1
**Summary** — `DefenseMissile` now gets a fixed velocity in `__init__` (zero vector for a zero-length shot, so it never calls `.normalize()` on one). `update()` either steps by `velocity * dt` or, if the remaining distance is `<= speed * dt`, snaps to the target and sets `reached_target`. `Explosion` (now only in `entities/terrain.py`, re-exported from `entities`) runs on `elapsed += dt` with a `0 → max → 0` radius and an `is_player` flag. `ExplosionPool.get_explosion` resets every per-use field. In `MainGame.update()`, missiles that have arrived detonate as player explosions. This happens straight after the defense-missile update loop and before the explosion update loop, so a new explosion advances one `dt` on the frame it is created. In `check_collisions()`, a check of active player explosions against incoming missiles (`distance <= radius`) replaces the 16x16 contact check.

**Deviation (criterion 12):** the spec's bound of "on or before frame 80" can't be reached alongside criterion 6. Explosions start at radius 0 and grow by `80 / 0.5 * DT_DEFAULT ≈ 2.67 px` per frame. The missile arrives on frame 75, so an incoming missile 20 px away is first inside the radius on frame 82 (`8 * 2.67 = 21.3`). If the explosion weren't updated on its spawn frame, that would be frame 83. The test asserts the kill happens between frames 75 and 82 and explains the arithmetic in its docstring. The rest of criterion 12 is asserted as written (kill happens, shake is `SCREEN_SHAKE_INTERCEPT`, `draw()` succeeds). If the frame-80 bound matters, a human needs to choose: a faster explosion, a larger initial radius, or a looser criterion.

**Commits**
- `9a86d6f 002-missiles-explode: straight-line defense missiles detonate at target; dt-based explosions kill incoming missiles`
- `3aa1b32 002-missiles-explode: tests for flight, detonation, explosion timeline and kill radius; rewrite intercept shake test`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Straight flight | `test_straight_flight` | Yes |
| 2 | Arrival on step 75, exact snap, stays | `test_arrival_on_step_75_and_stays` | Yes |
| 3 | No overshoot, on screen, 4 targets x 2 dts | `test_no_overshoot_stays_on_screen` (8 params) | Yes |
| 4 | Zero-length shot | `test_zero_length_shot` | Yes |
| 5 | Detonation through the game | `test_detonation_through_game` | Yes |
| 6 | Explosion timeline on dt | `test_explosion_timeline_on_dt` | Yes |
| 7 | No wall clock; 47 frames active, 49 inactive | `test_no_wall_clock`, `test_terrain_has_no_get_ticks` | Yes |
| 8 | Kill radius | `test_kill_radius` | Yes |
| 9 | Current radius, not max | `test_uses_current_radius_not_max` | Yes |
| 10 | Non-player explosions don't intercept | `test_non_player_explosions_do_not_intercept` | Yes |
| 11 | No contact detonation | `test_no_contact_detonation` | Yes |
| 12 | End to end | `test_end_to_end_intercept`: kill lands on frame 82, not ≤ 80 (see Deviation) | Partly (bound) |
| 13 | Rewritten shake intercept test | `tests/test_screen_shake.py::test_intercept_sets_shake_and_next_frame_draws`: still asserts the shake value, a non-integer float after decay, and `draw()`. Other tests in the file are unchanged | Yes |
| 14 | Pool reuse resets state | `test_pool_reuse_resets_state` (pool of size 1) | Yes |
| 15 | Single Explosion class | `test_single_explosion_class` | Yes |
| 16 | Missile drawn where it is | `test_missile_drawn_where_it_is` (this already passed on the old code; it stays as a guard) | Yes |
| 17 | Full suite headless, config.json unmodified | 33 passed; sha256 of `config.json` the same before and after | Yes |
| 18 | [visual] 37 updates: yellow dot halfway along a straight line | Rendered headless: one yellow dot at (208.7, 159.0), on the line from (20, 20) to (400, 300), nothing else in the sky | Yes |
| 19 | [visual] 75 + 15 updates: rings centred on (400, 300), radius about 40, no dot | Rendered headless: rings centred on (400, 300), outer radius 42.7, `defense_missiles == []` | Yes |

All other new tests failed on the old code (22 failed, 11 passed before the change).

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `33 passed in 1.02s`

**Notes**
- `systems/game_loop.py` still has an unused `Explosion` import from before this job. I left it alone because it isn't related to the contact check I removed.
- Player explosions still damage buildings within `EXPLOSION_MAX_RADIUS` of a building's top-left corner. That is out of scope here and belongs to backlog item 3.
