# 018-building-explosions: Fix building-in-explosion distance check and play a fiery explosion when a building is destroyed

## Problem
`CollisionSystem.building_in_explosion` (`systems/collision.py`) measures the distance from
`explosion.position` to `building.position` (the building's top-left corner) instead of the
nearest point on the building's rectangle. A blast centred right inside a building can therefore
miss it: for `Building(100, 500)` (`60x40`, bounds `100..160` × `500..540`), an explosion at
`(130, 520)` with `radius = 30` is at distance `sqrt(30² + 20²) ≈ 36.06 > 30` from `(100, 500)`
and returns `False`. In addition, when an enemy missile delivers the third, fatal hit to a
building, the game only spawns the same small, purplish-ringed impact explosion at the contact
point (`EXPLOSION_MAX_RADIUS = 80`) as on non-fatal hits, so losing a building looks no more
dramatic than a glancing hit.

## Scope
- **`CollisionSystem.building_in_explosion(building, explosion)`** (`systems/collision.py`):
  - Measure Euclidean distance from `explosion.position` to the nearest point on
    `building.get_bounds()` (`closest_x = max(rect.x, min(explosion.position.x, rect.right))`,
    `closest_y = max(rect.y, min(explosion.position.y, rect.bottom))`) and return
    `distance <= explosion.radius`, matching `CollisionSystem.building_to_explosion`.
- **New constants** in `game/constants.py` inside `# Explosion settings`:
  - `BUILDING_EXPLOSION_MAX_RADIUS = 110`: peak radius in px when a building is destroyed
    (larger than `EXPLOSION_MAX_RADIUS = 80`).
  - `BUILDING_EXPLOSION_EXPANSION_TIME = 0.4`: seconds to grow from `0` to
    `BUILDING_EXPLOSION_MAX_RADIUS`.
  - `BUILDING_EXPLOSION_SHRINK_TIME = 0.5`: seconds to shrink and fade from
    `BUILDING_EXPLOSION_MAX_RADIUS` back to `0`.
  - `BUILDING_EXPLOSION_LAYERS = ((1.0, COLOR_RED), (0.7, COLOR_ORANGE), (0.4, COLOR_YELLOW))`:
    `(radius_scale, color)` layers ordered from outer fireball to inner core.
  - `BUILDING_EXPLOSION_FLICKER_SPEED = 40.0`: angular speed (rad/s) for the fire flicker.
  - `BUILDING_EXPLOSION_FLICKER_AMOUNT = 0.12`: fractional radius modulation per layer.
- **Fiery building explosion on `Explosion` and `ExplosionPool`** (`entities/terrain.py`):
  - `Explosion.__init__(self, x, y, is_player=False, is_building=False)`:
    - Store `self.is_building = is_building`.
    - Set `self.max_radius = BUILDING_EXPLOSION_MAX_RADIUS if is_building else EXPLOSION_MAX_RADIUS`.
    - Set `self.expansion_time = BUILDING_EXPLOSION_EXPANSION_TIME if is_building else EXPLOSION_EXPANSION_TIME`.
    - Set `self.shrink_time = BUILDING_EXPLOSION_SHRINK_TIME if is_building else EXPLOSION_SHRINK_TIME`.
  - `Explosion.update(self, dt)`:
    - Use `self.expansion_time` and `self.shrink_time` so normal/player explosions still expand
      over `0.5` s and shrink over `0.3` s to `max_radius = 80`, while building explosions expand
      over `0.4` s and shrink over `0.5` s to `max_radius = 110`.
  - `Explosion.fade_alpha(self)` (new):
    - Return `0` when `not self.is_active` or `self.radius <= 0`.
    - Return `255` while expanding (`self.elapsed <= self.expansion_time`).
    - During the shrink phase (`self.expansion_time < self.elapsed < self.expansion_time + self.shrink_time`),
      return `max(0, min(255, round(255 * (1.0 - (self.elapsed - self.expansion_time) / self.shrink_time))))`.
  - `Explosion.fire_layers(self)` (new):
    - When `not self.is_active` or `self.radius <= 0`, return `[]`.
    - Otherwise return `[(layer_radius, color), ...]` for `i, (scale, color)` in
      `enumerate(BUILDING_EXPLOSION_LAYERS)` (outer `COLOR_RED`, middle `COLOR_ORANGE`, inner
      `COLOR_YELLOW`), where
      `flicker = 1.0 + BUILDING_EXPLOSION_FLICKER_AMOUNT * math.sin(self.elapsed * BUILDING_EXPLOSION_FLICKER_SPEED + i * 2.0)`
      and `layer_radius = max(0, round(self.radius * scale * flicker))`.
  - `Explosion.draw_explosion(self, screen)`:
    - When `self.is_building` is `False`, keep the existing 4-ring drawing unchanged.
    - When `self.is_building` is `True`: if `not self.is_active`, return. Get
      `layers = self.fire_layers()` and `alpha = self.fade_alpha()`. If `not layers`,
      `alpha <= 0`, or the largest `layer_radius <= 0`, return. Otherwise create a
      `pygame.SRCALPHA` surface sized to fit the largest `layer_radius`, draw each circle with
      `(*color, alpha)` from outer to inner at the surface centre, and blit it onto `screen`
      centred at `(int(self.position.x), int(self.position.y))`.
  - `ExplosionPool.get_explosion(self, x, y, is_player=False, is_building=False)`:
    - Accept `is_building=False`, pass it to `Explosion(x, y, is_player, is_building)` when
      allocating, and reset `is_building`, `max_radius`, `expansion_time`, and `shrink_time`
      alongside the existing fields when reusing a pooled instance.
- **Triggering on building destruction** (`systems/game_loop.py`, `MainGame.check_collisions`):
  - When an incoming missile hits a standing building, apply `building.take_impact()` first.
  - If `building.is_destroyed` is `True` after the impact, spawn the explosion at the building's
    centre `(building.position.x + building.width / 2, building.position.y + building.height / 2)`
    with `self.explosion_pool.get_explosion(cx, cy, is_building=True)`.
  - If `building.is_destroyed` is `False` (non-fatal hit), spawn the regular impact explosion at
    `(missile.position.x, missile.position.y)` with `is_building=False`, as today.
  - In both cases `is_player` is `False`, so building explosions neither intercept incoming
    missiles nor damage other buildings.
- **README**: add one bullet at the end of `## Features` describing the fiery explosion when a
  building is destroyed.
- **Tests**: add `tests/test_building_explosions.py`. Do not edit existing test files.

## Out of scope
- Debris particles, smoke plumes that linger after the explosion expires, or scorch marks on the
  ground.
- A separate sound effect or different screen-shake value for building destruction (the existing
  `"impact"` sound and `SCREEN_SHAKE_BUILDING_HIT` stay as they are).
- Awarding score points when a building is destroyed or changing building health /
  `damage_threshold`.
- Wiring `CollisionSystem` into `MainGame.check_collisions()`.
- Any change to defense-missile explosions (`is_player=True`) or non-fatal building-hit
  explosions (`is_player=False, is_building=False`).

## Acceptance criteria
Terms used below:
- **Building B** is `Building(100, 500)` (residential `60x40`, bounds `x` in `100..160` and `y`
  in `500..540`, centre `(130, 520)`).
- **Stub** means `types.SimpleNamespace(position=pygame.math.Vector2(x, y), radius=r)`.
- **Black surface draw** means creating `surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))`,
  filling it with `COLOR_BLACK`, and calling `explosion.draw_explosion(surf)`.

1. [test] **Constants.**
   - `BUILDING_EXPLOSION_MAX_RADIUS == 110` and `BUILDING_EXPLOSION_MAX_RADIUS > EXPLOSION_MAX_RADIUS`.
   - `BUILDING_EXPLOSION_EXPANSION_TIME == 0.4` and `BUILDING_EXPLOSION_SHRINK_TIME == 0.5`.
   - `BUILDING_EXPLOSION_LAYERS == ((1.0, COLOR_RED), (0.7, COLOR_ORANGE), (0.4, COLOR_YELLOW))`.
   - `BUILDING_EXPLOSION_FLICKER_SPEED == 40.0` and `BUILDING_EXPLOSION_FLICKER_AMOUNT == 0.12`.
2. [test] **`CollisionSystem.building_in_explosion` measures from the nearest point on the building.**
   Against Building B (`100..160` × `500..540`):
   - Centre inside the building: `(130, 520)` with `r = 30` gives `True`; `(130, 520)` with
     `r = 0` gives `True`.
   - Right edge: `(200, 520)` gives `True` at `r = 40` and `False` at `r = 39.5`.
   - Left edge: `(70, 520)` gives `True` at `r = 30` and `False` at `r = 29.5`.
   - Top edge: `(130, 460)` gives `True` at `r = 40` and `False` at `r = 39.5`.
   - Bottom edge: `(130, 570)` gives `True` at `r = 30` and `False` at `r = 29.5`.
   - Bottom-right corner `(160, 540)`: `(163, 544)` gives `True` at `r = 5` and `False` at
     `r = 4.9`.
   - Top-left corner `(100, 500)`: `(97, 496)` gives `True` at `r = 5` and `False` at `r = 4.9`.
   - For every point and radius above, `CollisionSystem.building_in_explosion(b, exp)` matches
     `CollisionSystem.building_to_explosion(b, exp)`.
3. [test] **Building explosion timeline and peak size.**
   `e = Explosion(130, 520, is_building=True)` starts with `is_building is True`,
   `is_player is False`, `radius == 0`, `max_radius == BUILDING_EXPLOSION_MAX_RADIUS == 110`,
   `expansion_time == 0.4`, `shrink_time == 0.5`, and `is_active is True`:
   - After `e.update(0.2)` (half expansion), `e.radius == pytest.approx(55.0)` and
     `e.fade_alpha() == 255`.
   - After another `e.update(0.2)` (`elapsed == 0.4`, peak),
     `e.radius == pytest.approx(110.0) > EXPLOSION_MAX_RADIUS` and `e.fade_alpha() == 255`.
   - After `e.update(0.25)` (`elapsed == 0.65`, halfway through shrink),
     `e.radius == pytest.approx(55.0)` and `e.fade_alpha() == pytest.approx(128, abs=1)`.
   - After `e.update(0.25)` (`elapsed == 0.9`), `e.is_active is False`, `e.radius == 0`,
     `e.fade_alpha() == 0`, and `e.fire_layers() == []`.
4. [test] **Layered orange/yellow/red fire and flicker.**
   - On `e = Explosion(400, 300, is_building=True)` after `e.update(0.4)` (peak, `radius == 110`),
     `layers = e.fire_layers()` has 3 entries with colours `[COLOR_RED, COLOR_ORANGE, COLOR_YELLOW]`
     and strictly decreasing positive integer radii `r_red > r_orange > r_yellow > 0`, with
     `r_red > EXPLOSION_MAX_RADIUS`.
   - Stepping `e` across 6 frames of `DT_DEFAULT` from `elapsed = 0.1` to `elapsed = 0.2`
     produces at least 3 distinct `(r_red, r_orange, r_yellow)` triples, and at every step
     `r_red > r_orange > r_yellow > 0`.
   - Calling `e.fire_layers()` and `e.draw_explosion(surf)` twice without calling `e.update()`
     produces identical layer radii and identical surface pixels (deterministic in `elapsed`,
     so a paused frame never flickers).
5. [test] **Rendered fire layers and fading on a surface.**
   - On `e = Explosion(400, 300, is_building=True)` at peak (`e.update(0.4)`), black surface draw:
     - Centre `(400, 300)` is `COLOR_YELLOW`.
     - Middle ring `(460, 300)` (60 px from centre) is `COLOR_ORANGE`.
     - Outer ring `(490, 300)` (90 px from centre, beyond `EXPLOSION_MAX_RADIUS = 80`) is
       `COLOR_RED`.
     - Outside `(530, 300)` is `COLOR_BLACK`.
   - After advancing into the shrink phase with `e.update(0.25)` (`elapsed == 0.65`,
     `fade_alpha() in (127, 128)`), black surface draw at `(400, 300)`: the centre pixel's R and
     G channels are between `115` and `140` (roughly half of `255`), strictly dimmer than the
     peak `(255, 255, 50)` and strictly brighter than `COLOR_BLACK`.
6. [test] **Pool reuse resets `is_building` and timing fields.**
   - With `pool = ExplosionPool(pool_size=1)`, `first = pool.get_explosion(130, 520, is_building=True)`
     has `is_building is True`, `max_radius == BUILDING_EXPLOSION_MAX_RADIUS`,
     `expansion_time == BUILDING_EXPLOSION_EXPANSION_TIME`, and
     `shrink_time == BUILDING_EXPLOSION_SHRINK_TIME`.
   - After returning `first` with `pool.return_explosion(first)`,
     `reused = pool.get_explosion(200, 200)` returns the same object with `is_building is False`,
     `is_player is False`, `max_radius == EXPLOSION_MAX_RADIUS`,
     `expansion_time == EXPLOSION_EXPANSION_TIME`, `shrink_time == EXPLOSION_SHRINK_TIME`,
     `radius == 0`, `elapsed == 0.0`, and `is_active is True`.
7. [test] **Non-fatal vs fatal building hits in `MainGame.check_collisions()`.**
   On `main_game` with `b = game.buildings[0]` (at `(30, 540)`, width `60`, height `40`, centre
   `(60, 560)`), hitting `b` at its top-left corner `(30, 540)` with a parked `IncomingMissile`:
   - **Hit 1** (`health_current == 66`, `not b.is_destroyed`): `len(game.explosions) == 1`; the
     explosion has `is_building is False`, `is_player is False`, `max_radius == EXPLOSION_MAX_RADIUS`,
     and `position == Vector2(30, 540)`.
   - **Hit 2** (`health_current == 32`, `not b.is_destroyed`): the new explosion again has
     `is_building is False` and `position == Vector2(30, 540)`.
   - **Hit 3** (`health_current == 0`, `b.is_destroyed is True`): the new explosion has
     `is_building is True`, `is_player is False`, `max_radius == BUILDING_EXPLOSION_MAX_RADIUS`,
     and `position == Vector2(60, 560)` (the building's centre, even though the missile hit the
     corner `(30, 540)`).
8. [test] **Building explosion does not intercept missiles or harm adjacent buildings.**
   On `main_game`, destroy `game.buildings[0]` (centre `(60, 560)`) with 3 missile impacts, then
   advance `0.4` s so the building explosion is at peak (`radius == 110`, which overlaps
   `game.buildings[1]` at `x = 110`):
   - `game.buildings[0]` is removed from `game.buildings`.
   - `game.buildings[1]` (`Building(110, 540)`) still has `health_current == 100`.
   - A parked `IncomingMissile` placed at `(60, 500)` (60 px from the explosion centre, well
     inside `radius == 110`) survives `game.check_collisions()`, and `game.score_system.score`
     does not increase by `MISSILE_INTERCEPT_POINTS`.
9. [test] **In-game rendering of a destroyed building's fireball.**
   On `main_game`, clear `game.explosions`, set `game.buildings[0].health_current = 34`, and
   deliver the fatal hit to `game.buildings[0]` (centre `(60, 560)`). Advance `game.update(0.4)`
   and call `game.draw()`:
   - `game.screen.get_at((60, 560))[:3] == COLOR_YELLOW` (hot core over the building centre).
   - `game.screen.get_at((60, 500))[:3] == COLOR_ORANGE` (60 px above centre).
   - `game.screen.get_at((60, 470))[:3] == COLOR_RED` (90 px above centre, higher than any
     defense blast of radius 80 could reach).
10. [test] All existing tests pass unchanged, including `tests/test_collision_score.py`,
    `tests/test_buildings_game_over.py`, and `tests/test_missiles_explode.py`.
11. [visual] **Peak building fireball vs defense blast.** On `main_game`, fire a defense missile
    that detonates at `(400, 300)` and simultaneously trigger a fatal building hit on
    `buildings[1]` (centre `(140, 560)`), then advance `0.4` s and call `draw()`. Over the
    destroyed building's footprint stands a large, concentric red/orange/yellow fireball visibly
    wider and taller than the defense explosion in the sky.
12. [visual] **Fading fireball.** Advance the scene from criterion 11 by another `0.3` s into the
    shrink phase and call `draw()`. The building fireball has shrunk, its rings have flickered to
    new proportions, and its red/orange/yellow layers blend translucently into the night sky and
    olive ground without any dark or black halo.

## Touch points
- `systems/collision.py`: `CollisionSystem.building_in_explosion`.
- `game/constants.py`: add `BUILDING_EXPLOSION_MAX_RADIUS`, `BUILDING_EXPLOSION_EXPANSION_TIME`,
  `BUILDING_EXPLOSION_SHRINK_TIME`, `BUILDING_EXPLOSION_LAYERS`,
  `BUILDING_EXPLOSION_FLICKER_SPEED`, and `BUILDING_EXPLOSION_FLICKER_AMOUNT` under
  `# Explosion settings`.
- `entities/terrain.py`: `Explosion.__init__`, `Explosion.update`, `Explosion.fade_alpha`,
  `Explosion.fire_layers`, `Explosion.draw_explosion`, and `ExplosionPool.get_explosion`.
- `systems/game_loop.py`: `MainGame.check_collisions` (building impact block).
- `README.md`: add one bullet under `## Features`.
- `tests/test_building_explosions.py` (new).

## Notes for reviewers
- **code:**
  - `ExplosionPool.get_explosion` must reset `is_building`, `max_radius`, `expansion_time`, and
    `shrink_time` on every reused object so a pooled building explosion never leaks its 110 px
    radius or fiery renderer into a subsequent player or non-fatal hit explosion (criterion 6).
  - Flicker must be a pure function of `self.elapsed` (via `math.sin`), never `random`, so
    `draw_scene()` stays read-only and deterministic while paused (`017-pause-overlay`).
  - `BUILDING_EXPLOSION_EXPANSION_TIME + BUILDING_EXPLOSION_SHRINK_TIME == 0.9` s (< 60 frames at
    `DT_DEFAULT`), so `test_buildings_game_over.py::test_city_redraws_without_destroyed_building`
    continues to see the explosion finish within 60 frames.
- **security:** No file, network, or config I/O changes. Tests use the `main_game` fixture (which
  patches `CONFIG_PATH`).
- **ux / ui:**
  - Drawing the fire layers onto a local `pygame.SRCALPHA` surface with `(*color, alpha)` and
    blitting once onto `screen` ensures the shrinking fireball fades smoothly into the blue sky
    and olive ground instead of darkening toward black.
  - Because `BUILDING_EXPLOSION_FLICKER_AMOUNT = 0.12` and layer scales are `1.0`, `0.7`, `0.4`,
    the three radii never cross (`0.4 * 1.12 < 0.7 * 0.88` and `0.7 * 1.12 < 1.0 * 0.88`), so the
    yellow core, orange middle, and red outer ring remain distinct on every frame.
