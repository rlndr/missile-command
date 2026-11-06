STATUS: READY

## Round 1
**Summary** — Added one test file, `tests/test_collision_score.py` (304 lines, all tests; no production changes). It pins the current main behaviour of `get_distance`/`check_circle_collision`, every `CollisionSystem` check except `building_in_explosion`, the building AABB / player-blast radius / spent-blast edges of `MainGame.check_collisions()`, and `ScoreSystem` hit, building, mixed-total and reset arithmetic. Every criterion matched main as written; nothing needed reporting as a mismatch. Mutation checks (each reverted afterwards) confirm the tests catch regressions: changing `<=` to `<` in `check_circle_collision`, the `CollisionSystem` AABB, `missile_in_explosion`, the game-loop AABB or the game-loop blast check; changing the hard-coded missile radius 8 to 7; ignoring `is_active` for player blasts; `reset()` not clearing `time_survived`; and `add_building_destroyed` not counting. Each one makes 1–7 tests fail.

**Commits**
`2472371 011-collision-score-tests: tests for collision boundaries and score calculation`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| C | File constraints: no draw calls, no `MainGame.update()`, no launcher constants / `base.position` / `get_bounds()` on a real base, no `DefenseMissile` | grep finds only `Explosion.update(...)` calls (lines 51, 164) and none of the forbidden names | Yes |
| S | Shared setup: SimpleNamespace stubs, `main_game` + `random.seed(0)`, parked missiles, `CONFIG_PATH` patched before `ScoreSystem()`, Building B | `_stub`, `_park`, `_player_blast`, `game` and `scores` fixtures, `_building_b` | Yes |
| 1 | `get_distance` | `test_get_distance_accepts_tuples_and_vectors_and_is_symmetric` | Yes |
| 2 | `check_circle_collision` inclusive | `test_check_circle_collision_is_inclusive[...]` (3 cases), `test_check_circle_collision_zero_radii_same_point` | Yes |
| 3 | `missile_to_missile_collision` radii 8 + 5 | `test_missile_to_missile_uses_radii_8_and_5[...]` (3 cases) | Yes |
| 4 | `missile_to_building_collision` inclusive edges | `test_missile_to_building_is_inclusive_on_every_edge[...]` (9 cases) | Yes |
| 5 | `missile_to_base_collision` with stub base | `test_missile_to_base_is_inclusive[...]` (5 cases) | Yes |
| 6 | `building_to_building_collision` follows colliderect | `test_building_to_building_follows_colliderect[...]` (4 cases), `test_building_to_building_with_itself` | Yes |
| 7 | `missile_in_explosion` inclusive, real Explosion at r=40 | `test_missile_in_explosion_is_inclusive[...]` (5 cases; fixture asserts `radius == 40`) | Yes |
| 8 | `building_to_explosion` closest point | `test_building_to_explosion_uses_closest_point[...]` (7 cases) | Yes |
| 9 | Game building hit box inclusive | `test_check_collisions_building_hit_box_is_inclusive[...]` (4 hit, 4 miss; health 66/100, explosion count and `is_player`, score 0) | Yes |
| 10 | Player-blast radius inclusive | `test_check_collisions_player_blast_radius_is_inclusive` | Yes |
| 11 | Spent player blast kills nothing | `test_check_collisions_spent_player_blast_kills_nothing` | Yes |
| 12 | `add_missile_hit` default/custom | `test_add_missile_hit_default_and_custom_points` | Yes |
| 13 | `add_building_destroyed` | `test_add_building_destroyed_adds_score_value` | Yes |
| 14 | Mixed total, then reset | `test_mixed_total_then_reset_keeps_high_score` | Yes |
| 15 | Full suite passes; config.json unchanged | Full suite 217 passed; `sha256sum -c` on `config.json` before/after: OK | Yes |

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `217 passed in 6.81s` (52 of them new).

**Notes**
- The local `game` fixture empties `buildings`, `incoming_missiles` and `explosions` after `start_game()`. Criteria 10 and 11 then don't depend on the start layout, which 009 may change. Criterion 9 still sets `game.buildings = [Building(300, 400)]` and `game.explosions = []` itself, as the spec asks.
- `_stub` turns a `position` tuple into a `pygame.math.Vector2`, so every stub's `position` is a Vector2 as required.
- The file is 304 lines, above the spec's 180–250 estimate. The extra length is docstrings and one-row-per-point parametrize tables.
- Findings logged for later jobs, unchanged from the spec: `CollisionSystem` is unused by the game; `building_in_explosion` measures from the top-left corner; `missile_to_missile_collision` hard-codes radii 8/5; building loss scores nothing in play (GAME_DESIGN.md §8).
