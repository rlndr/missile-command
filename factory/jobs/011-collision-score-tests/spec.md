# 011-collision-score-tests: Unit tests for collision detection and score calculation

## Problem
GAME_DESIGN.md §13 asks for pytest coverage of "collision detection accuracy" and "score
calculation correctness". Today the edges of every collision check are untested. Nothing
pins whether touching counts as a hit for circles, rects or blast radii. The geometry helpers
in `utils/vector_math.py` and the whole `CollisionSystem` class in `systems/collision.py`
have no tests at all. `ScoreSystem.add_building_destroyed()`, `add_missile_hit()` with
custom points, and `reset()` keeping `high_score` are untested too. A regression in any of
these would go unnoticed.

## Scope
- Add one new test file, `tests/test_collision_score.py`. It pins the **current main**
  behaviour of:
  - `utils/vector_math.py`: `get_distance()` and `check_circle_collision()`.
  - `systems/collision.py`, `CollisionSystem`: `missile_to_missile_collision`,
    `missile_to_building_collision`, `missile_to_base_collision`,
    `building_to_building_collision`, `missile_in_explosion` and `building_to_explosion`.
  - The boundaries of `MainGame.check_collisions()`:
    - The building AABB is inclusive on all four edges.
    - The player-blast radius is inclusive (`distance <= radius`).
    - A spent (inactive) player explosion kills nothing.
  - `systems/score.py`, `ScoreSystem`:
    - `add_missile_hit()` with default and custom points.
    - `add_building_destroyed()`.
    - A mixed total from hits, buildings and survival time.
    - `reset()`.
- Test-only job. **No production file changes** (`main.py`, `entities/`, `systems/`,
  `game/`, `utils/`, `README.md` and `config.json` stay untouched). No new constants.
- If a criterion below doesn't match what main actually does, don't change game code to make
  it pass. Stop and report the mismatch in the build notes.

## Out of scope
- **Movement speed consistency.** §13 lists it, but `tests/test_missiles_explode.py`
  already covers defense-missile flight. Incoming-missile speed is left to a later job.
- **Explosion timeline.** Grow/shrink timing is already covered by
  `test_explosion_timeline_on_dt`. Here, explosions are used only as fixed-radius inputs.
- **`CollisionSystem.building_in_explosion`.** It measures from `building.position`, the
  top-left corner, not the building's area (see Notes). Pinning that quirk would block
  fixing it, so leave it untested.
- **Points for destroyed buildings in play.** `check_collisions()` never calls
  `add_building_destroyed()`, which differs from GAME_DESIGN.md §8. Don't assert either way
  that building loss scores in the game loop.
- **Survival bonus, intercept-once and overlapping-blast scoring, HUD text and high-score
  file I/O.** Already covered by `tests/test_scoring.py`, `tests/test_buildings_game_over.py`
  and `tests/test_load_high_score.py`. Don't duplicate them.
- `ScoreDisplay` (unused by the game) and anything drawn on screen.
- **Anything about the launcher's position or how enemy missiles are drawn.** Jobs
  009-bottom-launcher and 010-enemy-exhaust-trails change these in parallel (see
  constraints below).
- Deleting or refactoring the unused `CollisionSystem`.

## Acceptance criteria
**Test file constraints (they keep this job from conflicting with 009 and 010):**
- Never call `MainGame.draw()`, `draw_missile()`, `draw_base()` or any other draw method.
- Never call `MainGame.update()`.
- Never read `LAUNCHER_X_OFFSET`/`LAUNCHER_Y_OFFSET`, `game.base.position` or
  `DefensiveBase.get_bounds()`.
- Never construct a `DefenseMissile`.

**Shared setup:**
- **Stubs** are `types.SimpleNamespace` objects with only the attributes the function reads
  (`position` as a `pygame.math.Vector2`, `radius`, `get_bounds`, `score_value`).
- **Game tests** use the `main_game` fixture from `tests/conftest.py` with
  `random.seed(0)`.
- A **parked missile** is an `IncomingMissile` whose `position` is set to the given point
  and whose `velocity` is `Vector2(0, 0)`, as in `tests/test_scoring.py::_park`.
- **Score tests** build `ScoreSystem()` only after monkeypatching `systems.score.CONFIG_PATH`
  to a file under `tmp_path`.
- **Building B** is `Building(100, 500)` (residential: 60 x 40, so its bounds are x 100..160
  and y 500..540).

### Geometry helpers
1. [test] **`get_distance`.**
   - `get_distance((0, 0), (3, 4)) == 5.0`.
   - `get_distance(Vector2(3, 4), (0, 0)) == 5.0`. It accepts tuples or Vector2 and is
     symmetric.
   - `get_distance((7, 7), (7, 7)) == 0.0`.
2. [test] **`check_circle_collision` is inclusive.** With radii 8 and 5, centred on (0, 0)
   and the second point:
   - (13, 0) gives True (touching).
   - (5, 12) gives True (distance exactly 13).
   - (13.01, 0) gives False.
   - `check_circle_collision((1, 1), 0, (1, 1), 0)` gives True.

### CollisionSystem
3. [test] **`missile_to_missile_collision` uses radii 8 + 5.** The incoming stub is at
   (200, 200). A defense stub at (213, 200) gives True, at (200, 187) gives True, and at
   (213.5, 200) gives False.
4. [test] **`missile_to_building_collision` is inclusive on every edge of Building B.**
   - True for missile stubs at (100, 500), (160, 500), (100, 540), (160, 540) and
     (130, 520).
   - False at (99.5, 520), (160.5, 520), (130, 499.5) and (130, 540.5).
5. [test] **`missile_to_base_collision`** uses a base stub whose `get_bounds()` returns
   `pygame.Rect(10, 10, 60, 30)`, not a real `DefensiveBase`.
   - True at (10, 10), (70, 40) and (40, 25).
   - False at (70.5, 25) and (40, 9.5).
6. [test] **`building_to_building_collision` follows `Rect.colliderect`.** Building B
   against:
   - `Building(159, 500)` gives True.
   - `Building(160, 500)` gives False (a shared vertical edge is not a collision).
   - `Building(100, 539)` gives True.
   - `Building(100, 540)` gives False.
   - Building B itself gives True.
7. [test] **`missile_in_explosion` is inclusive.**
   - Setup: a real `Explosion(400, 300)` after `update(0.25)` has `radius == 40` (exactly,
     since `EXPLOSION_MAX_RADIUS * 0.25 / EXPLOSION_EXPANSION_TIME == 40.0`).
   - True for missile stubs at (440, 300), (424, 332) and (400, 260), all at distance
     exactly 40.
   - False at (440.5, 300) and (400, 340.5).
8. [test] **`building_to_explosion` uses the closest point on the rect.** Building B against
   explosion stubs:
   - Centre (130, 520), radius 0: True (the centre is inside the rect).
   - Centre (200, 520): radius 40 gives True, radius 39.5 gives False.
   - Centre (163, 544), the corner case, nearest point (160, 540): radius 5 gives True,
     radius 4.9 gives False.
   - Centre (130, 460): radius 40 gives True, radius 39.5 gives False.

### MainGame.check_collisions boundaries
9. [test] **Building hit box is inclusive.** Parametrised. Each case:
   - Set `game.buildings = [Building(300, 400)]` and `game.explosions = []`.
   - Add one parked missile and call `check_collisions()` once.
   - **Hit cases**, at (300, 400), (360, 400), (300, 440) and (360, 440): the missile
     `is_destroyed`, the building has `health_current == 66`, and `len(game.explosions) == 1`
     with `game.explosions[0].is_player is False`.
   - **Miss cases**, at (299.5, 420), (360.5, 420), (330, 399.5) and (330, 440.5): the
     missile is not destroyed, `health_current == 100` and `game.explosions == []`.
   - In every case `game.score_system.score == 0`.
10. [test] **Player-blast radius is inclusive.**
    - Setup: one player blast, `game.explosion_pool.get_explosion(400, 300, is_player=True)`,
      appended to `game.explosions` and advanced with `update(0.25)` to radius 40.
    - Parked missiles at (440, 300) and (400, 260) are destroyed.
    - Parked missiles at (440.5, 300) and (376, 332.5) (distance about 40.4) survive.
    - After one `check_collisions()`, `score == 2 * MISSILE_INTERCEPT_POINTS` and
      `total_missiles_hit == 2`.
11. [test] **A spent player blast kills nothing.**
    - Setup: a player blast at (400, 300) advanced with
      `update(EXPLOSION_EXPANSION_TIME + EXPLOSION_SHRINK_TIME + 0.01)` has
      `is_active is False` and `radius == 0`.
    - It stays in `game.explosions`. A parked missile at exactly (400, 300) survives one
      `check_collisions()`, and `score == 0`.

### ScoreSystem
12. [test] **`add_missile_hit`.** On a fresh `ScoreSystem()`:
    - `add_missile_hit()` gives `score == MISSILE_INTERCEPT_POINTS == 10` and
      `total_missiles_hit == 1`.
    - Then `add_missile_hit(25)` gives `score == 35` and `total_missiles_hit == 2`.
    - `buildings_destroyed` stays 0 and `time_survived` stays 0.0.
13. [test] **`add_building_destroyed`.** On a fresh `ScoreSystem()`:
    - `add_building_destroyed(Building(0, 0))` adds
      `BUILDING_TYPES["residential"]["score_value"]`, which is 50. Then
      `buildings_destroyed == 1`.
    - Then a stub with `score_value=75` gives `score == 125` and `buildings_destroyed == 2`.
    - `total_missiles_hit` stays 0.
14. [test] **Mixed total, then reset.**
    - Setup: a fresh `ScoreSystem()` with `high_score` set to 500.
    - 3 × `add_missile_hit()`, 1 × `add_building_destroyed(Building(0, 0))` and
      `add_survival_time(2.5)` give `score == 3*10 + 50 + 2 == 82`.
    - `reset()` sets `score`, `total_missiles_hit` and `buildings_destroyed` to 0 and
      `time_survived` to 0.0 (a float). `high_score` stays 500.
    - Then `add_survival_time(0.5)` leaves `score == 0` (the old 0.5 s fraction did not
      carry over).

### Suite
15. [test] **All tests pass.**
    - The full suite, including every existing test unchanged, passes with the README
      command
      (`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q`).
    - The real `config.json` is byte-for-byte unchanged afterwards.

There are no `[visual]` criteria: this job changes nothing on screen.

## Touch points
- `tests/test_collision_score.py`: the only file added or changed.
  - Small helpers: `_stub(**attrs)`, `_park(game, x, y)` and `_player_blast(game, x, y, dt)`.
  - Use `pytest.mark.parametrize` for the point tables in criteria 2–9.
- Imports used:
  - `utils.vector_math.get_distance`, `check_circle_collision`.
  - `systems.collision.CollisionSystem`.
  - `entities.Building`, `IncomingMissile`.
  - `entities.terrain.Explosion`.
  - `systems.score.ScoreSystem`.
  - From `game.constants`: `MISSILE_INTERCEPT_POINTS`, `BUILDING_TYPES`,
    `EXPLOSION_EXPANSION_TIME`, `EXPLOSION_SHRINK_TIME`.
- No changes to `game/constants.py`. Expected diff: about 180–250 lines, all tests.

## Notes for reviewers
- **code:**
  - Check that every point table really sits on or just past the boundary it claims to
    test. Boundaries use 0.5 px (or 0.01/0.1 for radii) so float error can't flip a result.
  - Building positions must be integers, because `get_bounds()` builds a `pygame.Rect`,
    which holds ints.
  - Criterion 9 must replace `game.buildings` with a single test-placed building rather
    than rely on `start_game()`'s layout, which 009-bottom-launcher may change.
  - Confirm the file follows the constraints above: no draw calls, no `update()`, no
    launcher constants or base position, no `DefenseMissile`.
- **Findings to log (do not fix in this job):**
  - `CollisionSystem` is never called by the game. `check_collisions()` repeats the AABB and
    radius logic inline. A later job could wire one into the other or delete the class.
  - `CollisionSystem.building_in_explosion` measures from the building's top-left
    `position`. A blast centred inside a building can miss it: Building B with a blast at
    (130, 520), radius 30, is at distance about 36.1, so it returns False.
  - `missile_to_missile_collision` hard-codes radii 8 and 5 instead of reading
    `incoming.radius` and `defense.radius`.
  - Building loss awards no points in play, unlike GAME_DESIGN.md §8.
- **security:**
  - Tests must patch `systems.score.CONFIG_PATH` before building any `ScoreSystem` (the
    `main_game` fixture already does this for `MainGame`).
  - There is no other file I/O and no network access.
- **ux / ui:** Nothing player-facing changes, so there is nothing to review.
