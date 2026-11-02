# 002-missiles-explode: Defense missiles fly straight to the click and explode there

## Problem
The player can't shoot anything down. `DefenseMissile.update()` re-aims every frame at a
"lookahead" point 20 px ahead of itself horizontally, at the target's height. The missile
curves toward that height and then keeps sliding sideways until it leaves the screen. It
never checks whether it has reached the click point, so it never detonates. Separately,
`Explosion.update()` measures its age with `pygame.time.get_ticks()` instead of the `dt` it
receives, so explosion size depends on wall-clock time, not game time. In a fast headless
loop the explosion reaches radius 0 on its first update and goes inactive straight away,
which makes explosions impossible to test. The only way an enemy missile is destroyed
today is a defense missile flying right into its 16x16 box, which almost never happens.

## Scope
- **`DefenseMissile` moves in a straight line.** Its velocity is set once in `__init__`
  (normalised direction from launcher `(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)` to the target,
  times `DEFENSE_MISSILE_SPEED`) and never changes. Remove the lookahead/lerp steering.
- **Arrival.** Add a bool attribute `DefenseMissile.reached_target` (`False` at construction).
  In `update(dt)`, if the distance left to the target is `<= DEFENSE_MISSILE_SPEED * dt`, set
  `position` to exactly the target, set `reached_target = True`, and don't move again.
  Otherwise move by `velocity * dt`. If the target is the launcher position (distance 0), the
  constructor must not raise and the first `update()` arrives.
- **Detonation in `MainGame.update()`.** After defense missiles are updated, each missile
  with `reached_target` that isn't destroyed gets one player explosion at its target
  (`explosion_pool.get_explosion(target.x, target.y, is_player=True)`), appended to
  `self.explosions`, and the missile is `destroy()`ed. The existing filter removes it from
  `defense_missiles` on the next `update()`.
- **`Explosion` runs on `dt`.**
  - Store accumulated age in `self.elapsed` (seconds, starts at `0.0`) and remove `start_time`.
  - Every explosion starts at `radius = 0` and uses `max_radius = EXPLOSION_MAX_RADIUS`.
  - `update(dt)` adds `dt` to `elapsed`, then:
    - if `elapsed < EXPLOSION_EXPANSION_TIME`: `radius = max_radius * elapsed / EXPLOSION_EXPANSION_TIME`
    - else if `elapsed < EXPLOSION_EXPANSION_TIME + EXPLOSION_SHRINK_TIME`:
      `radius = max_radius * (1 - (elapsed - EXPLOSION_EXPANSION_TIME) / EXPLOSION_SHRINK_TIME)`
    - otherwise `radius = 0` and `is_active = False`.
  - Whether the explosion is active depends on `elapsed`, not on `radius <= 0`. A new
    explosion at radius 0 is still active.
  - No `pygame.time.get_ticks()` anywhere in `entities/terrain.py`.
- **Player flag.** New signatures `Explosion(x, y, is_player=False)` and
  `ExplosionPool.get_explosion(x, y, is_player=False)`. The old `radius` argument and the
  "radius 0 means instant full-size explosion" branch are removed. `get_explosion` must
  reset every per-use field when it reuses a pooled object: `position`, `radius = 0`,
  `elapsed = 0.0`, `is_active = True`, `is_player`. The building-hit call in
  `check_collisions` drops its magic `30` and makes a non-player explosion.
- **Explosions kill enemy missiles.** In `MainGame.check_collisions()`, replace the
  defense-missile vs incoming-missile 16x16 contact check with this: for each active
  explosion with `is_player == True`, every non-destroyed `IncomingMissile` whose centre is
  within the explosion's *current* `radius` (`distance <= radius`) is `destroy()`ed, and
  `shake_intensity` is set to `SCREEN_SHAKE_INTERCEPT`. Defense missiles no longer collide
  with anything on the way to their target. Non-player explosions (building hits) don't
  destroy incoming missiles.
- **Remove the duplicate `Explosion` class** in `entities/base.py`. `entities/__init__.py`
  imports `Explosion` from `.terrain` so that `from entities import Explosion` keeps working.
- **Tests:** new `tests/test_missiles_explode.py` covering the criteria below. Rewrite
  `test_intercept_sets_shake_and_next_frame_draws` in `tests/test_screen_shake.py` so the
  intercept comes from a player explosion, not from contact (criterion 13).
- Fix the `DefenseMissile` docstring ("curved trajectory" → straight line, detonates at
  target).

## Out of scope
- Player explosions damaging buildings. The explosion-vs-building loop in
  `check_collisions` stays as it is, so a player explosion within `EXPLOSION_MAX_RADIUS` of a
  building's top-left corner will damage it. Backlog item 3 fixes this.
- Score for destroyed enemy missiles and the survival-time truncation bug (backlog item 5).
- Enemy spawn timing still uses `pygame.time.get_ticks()` (backlog item 4). Pause and game
  states are also item 4.
- Chain reactions: an enemy missile destroyed by an explosion does not spawn its own
  explosion.
- Missile trails, a target "X" marker, a different explosion size for player shots, and
  changes to explosion ring colours/drawing.
- The launcher cooldown starting full (`DefensiveBase.cooldown_time = BASE_COOLDOWN_TIME`
  at construction), which blocks firing for the first 1.5 s.
- Updating `GAME_DESIGN.md` §4.1 (it still describes a curved trajectory and `turn_rate`).
- Using or cleaning up `systems/collision.py`. The builder may call
  `CollisionSystem.missile_in_explosion` if it fits, but doesn't have to.

## Acceptance criteria
Unless a criterion says otherwise, tests use the `main_game` fixture (no random spawns),
`random.seed(0)`, and `DT_DEFAULT`. When a test fires through the game it first sets
`game.base.cooldown_time = 0`. "Stationary incoming missile" means an `IncomingMissile` with
`position` set as stated and `velocity = Vector2(0, 0)`.

1. [test] **Straight flight:** `m = DefenseMissile(Vector2(400, 300))`. Over 74 calls to
   `m.update(DT_DEFAULT)`, `m.velocity` stays equal to its value after construction. Every
   position lies on the line from `(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)` to `(400, 300)`
   (perpendicular distance `< 1e-6`). After `n` updates the distance travelled from the
   launcher is `n * DEFENSE_MISSILE_SPEED * DT_DEFAULT` (within `1e-6`).
2. [test] **Arrival:** for the same missile, `reached_target` is `False` after 74 updates
   and `True` after the 75th. After the 75th, `m.position == Vector2(400, 300)` exactly.
   (The distance is about 472.02 px and each step is about 6.33 px, so arrival is on step 75.)
   More updates don't move it.
3. [test] **No overshoot, stays on screen:** for targets `(780, 580)`, `(20, 580)`,
   `(780, 20)` and `(400, 300)`, and for both `dt = DT_DEFAULT` and `dt = 0.16` (the game
   loop's dt cap), calling `update(dt)` until `reached_target` (at most 300 calls) keeps
   every position within `0 <= x <= SCREEN_WIDTH` and `0 <= y <= SCREEN_HEIGHT`. It ends
   with `position == target` exactly.
4. [test] **Zero-length shot:** `DefenseMissile(Vector2(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET))`
   constructs without raising, and one `update(DT_DEFAULT)` sets `reached_target = True`
   with the position unchanged.
5. [test] **Detonation through the game:** `game.spawn_defense_missile((400, 300))`. After
   74 `game.update(DT_DEFAULT)` calls, `game.explosions` is empty and the missile isn't
   destroyed. After the 75th, the missile `is_destroyed`, `game.explosions` holds exactly
   one explosion, and that explosion has `is_player is True` and
   `position == Vector2(400, 300)`. After one more `update()`, `game.defense_missiles == []`.
6. [test] **Explosion timeline on dt:** take a fresh explosion from
   `ExplosionPool().get_explosion(100, 100)`. It has `radius == 0`, `elapsed == 0.0`,
   `is_active is True`, and is still active after `update(0.0)`. Then:
   `update(0.25)` → `radius == approx(EXPLOSION_MAX_RADIUS * 0.5)` (40);
   `update(0.25)` → `radius == approx(EXPLOSION_MAX_RADIUS)` (80);
   `update(0.15)` → `radius == approx(EXPLOSION_MAX_RADIUS * 0.5)`;
   `update(0.2)` → `is_active is False`, `radius == 0`.
7. [test] **Frame-rate based, not wall clock:** with `pygame.time.get_ticks` monkeypatched
   to raise `AssertionError`, constructing a `DefenseMissile`, updating it to arrival,
   getting an explosion from a pool, and calling `Explosion.update()` all succeed. A fresh
   explosion updated 47 times with `DT_DEFAULT` is still active; after 49 it is inactive.
8. [test] **Kill radius:** append `e = game.explosion_pool.get_explosion(400, 300, is_player=True)`
   to `game.explosions` and call `e.update(0.25)` (radius about 40). Add stationary incoming
   missiles at `(400, 300)`, `(430, 300)`, `(400, 335)`, `(370, 310)` (all inside) and at
   `(450, 300)`, `(400, 360)` (outside). After `game.check_collisions()`, the four inside
   are `is_destroyed` and the two outside aren't, and
   `game.shake_intensity == SCREEN_SHAKE_INTERCEPT`.
9. [test] **Uses current radius, not max:** a player explosion at `(400, 300)` after
   `update(0.25)` plus a stationary incoming missile at `(460, 300)` (distance 60): after
   `check_collisions()` the missile is not destroyed. After another `e.update(0.2)`
   (radius about 72) and `check_collisions()`, it is destroyed.
10. [test] **Non-player explosions don't intercept:** `get_explosion(400, 300)` (default
    `is_player=False`) after `update(0.25)` plus a stationary incoming missile at
    `(410, 300)`: after `check_collisions()` the missile is not destroyed and
    `shake_intensity == 0`.
11. [test] **No contact detonation:** a stationary incoming missile at `(210, 160)`, which
    is on the flight path from the launcher to `(400, 300)` and about 236 px from it. Fire
    at `(400, 300)` and run 75 frames of `update(DT_DEFAULT)` + `check_collisions()`.
    Through frame 74 `game.explosions` is empty and the defense missile isn't destroyed.
    At the end the incoming missile at `(210, 160)` is still not destroyed.
12. [test] **End to end:** a stationary incoming missile at `(420, 300)`. Fire at
    `(400, 300)` and run `update(DT_DEFAULT)` + `check_collisions()` frames. The incoming
    missile is destroyed on or before frame 82, and once it is,
    (Amended by the human at approval: originally frame 80, which criterion 6's
    timeline makes impossible — the explosion first reaches 20 px on frame 82.)
    `shake_intensity == SCREEN_SHAKE_INTERCEPT`. Then `draw()` succeeds.
13. [test] **Rewritten shake intercept test** (`tests/test_screen_shake.py`): a player
    explosion from `game.explosion_pool.get_explosion(400, 200, is_player=True)` after
    `update(0.25)`, with a live incoming missile at `(408, 208)`. After `check_collisions()`
    the incoming missile is destroyed and `shake_intensity == SCREEN_SHAKE_INTERCEPT`. The
    next `update(DT_DEFAULT)` leaves a non-integer float and `draw()` doesn't raise. The
    other tests in that file pass unchanged.
14. [test] **Pool reuse resets state:** get `is_player=True` from a pool, update it until
    inactive, `return_explosion()` it, then `get_explosion(10, 20)`. Repeat until that same
    object comes back (or use a pool of size 1). The reused object has `is_player is False`,
    `radius == 0`, `elapsed == 0.0`, `is_active is True` and `position == Vector2(10, 20)`.
15. [test] **Single Explosion class:** `from entities import Explosion` and
    `from entities.terrain import Explosion` are the same object, and `entities/base.py`
    no longer defines `Explosion`.
16. [test] **Missile is drawn where it is:** fire at `(400, 300)`, run 37 updates, call
    `draw()`. `game.screen.get_at((int(m.position.x), int(m.position.y)))[:3] == COLOR_YELLOW`.
17. [test] The full suite passes headless with the README command (`SDL_VIDEODRIVER=dummy
    SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest
    python -m pytest -q`), and `config.json` is unmodified afterwards.
18. [visual] Fire at `(400, 300)`, run 37 updates, `draw()`, `pygame.image.save`. The frame
    shows a single `COLOR_YELLOW` dot (radius 5) about halfway along a straight line from
    the top-left launcher to (400, 300), with nothing drifting off to the side.
19. [visual] Same shot, 75 + 15 updates, `draw()`, save. The frame shows the explosion
    rings (same drawing as before) centred on (400, 300), with an outer radius of about
    40 px. The yellow defense-missile dot is gone.

## Touch points
- `entities/missile.py`: `DefenseMissile.__init__` (adds `reached_target`, safe zero-length
  direction) and `DefenseMissile.update` (straight-line step with snap-to-target; the
  lookahead/lerp code goes).
- `entities/terrain.py`: `Explosion.__init__(x, y, is_player=False)`,
  `Explosion.update(dt)` (based on `elapsed`), `ExplosionPool.get_explosion(x, y,
  is_player=False)` (full reset of every field). `draw_explosion` is unchanged.
- `entities/base.py`: delete the duplicate `Explosion` class.
- `entities/__init__.py`: import `Explosion` from `.terrain`.
- `systems/game_loop.py`:
  - `MainGame.update()`: detonate missiles that arrived, after the defense-missile update loop.
  - `MainGame.check_collisions()`: player explosion vs incoming missiles replaces the
    16x16 contact check; the building-hit `get_explosion` call loses its `30`.
- `tests/test_missiles_explode.py` (new). `tests/test_screen_shake.py`: rewrite the
  intercept test only.
- `game/constants.py`: no new constants. Use the existing `DEFENSE_MISSILE_SPEED`,
  `EXPLOSION_MAX_RADIUS`, `EXPLOSION_EXPANSION_TIME`, `EXPLOSION_SHRINK_TIME`,
  `SCREEN_SHAKE_INTERCEPT`, `LAUNCHER_X_OFFSET`, `LAUNCHER_Y_OFFSET`.

Expected diff: about 70 lines of game code changed or removed (plus about 45 deleted from
`entities/base.py`), and about 250 lines of tests.

## Notes for reviewers
- **code:** Check that `Explosion` activity is driven by `elapsed`. The old
  `if self.radius <= 0: is_active = False` would kill a radius-0 explosion on its first
  update. Check that `get_explosion` resets `is_player` and `elapsed` on pooled objects, so a
  reused building-hit explosion can't inherit `is_player=True` and the reverse. Arrival must
  snap to the target, not use float equality or "passed the target" sign tests that can
  miss with `dt = 0.16`. The zero-length direction must not call `.normalize()` on a zero
  vector (pygame raises `ValueError`). The removed contact check shouldn't leave unused
  helpers or imports behind. Tests must not depend on wall-clock time: no `time.sleep`, and
  no asserting on spawns.
- **code / test integrity:** Criterion 13 rewrites an existing test because the behaviour
  it pinned (contact intercept) is being removed on purpose. Confirm the rewrite still
  asserts the shake value and the float-decay `draw()` path, so it isn't weakened.
- **security:** Same as before: tests must never write the real `config.json`, and there are
  no new dependencies. Firing input is still only `event.pos` from a left click, so there's
  no new input surface.
- **ux:** Player-facing change: clicking now produces an explosion at the click point that
  clears enemy missiles inside it. Known gaps, all deferred to later backlog items: kills
  score nothing (item 5); a player explosion near the city damages buildings (item 3); you
  can't fire for the first 1.5 s after start because of the existing cooldown. Flag
  anything that feels worse than before, such as flight time to far corners (about 2 s to
  (780, 580)).
- **ui:** Explosion drawing code is unchanged. What's new is that explosions now grow and
  shrink visibly over about 0.8 s of game time. Check frames 18 and 19: the missile path is
  straight and the explosion is centred on the click.
