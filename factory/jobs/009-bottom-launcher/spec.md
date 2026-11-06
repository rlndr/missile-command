# 009-bottom-launcher: Launcher tower at the bottom centre of the screen

## Problem
The launcher is a white block in the top-left corner (`LAUNCHER_X_OFFSET`, `LAUNCHER_Y_OFFSET` = 20, 20),
partly off-screen at the tube. Defense missiles start there and fly down and across the screen,
so the player defends the city from the sky instead of from the ground. The city has no ground under
it: its 8 buildings sit off-centre (x 30–650 on an 800 px screen) over 20 px of sky. This job
moves the launcher to a tower standing on a ground strip at the bottom centre. The city is split
into two equal halves either side of the tower, and missiles rise from the tower's barrel toward
the click.

## Scope
- **Ground strip.** `MainGame.draw()` fills `Rect(0, GROUND_Y, SCREEN_WIDTH, GROUND_HEIGHT)`
  (`Rect(0, 580, 800, 20)`) with `COLOR_GROUND`. It is drawn straight after the sky gradient and
  before the launcher and buildings. Buildings already end at y = 580, so they stand on it.
- **City layout.** `MainGame.start_game()` places the 8 starting buildings in two groups of 4,
  mirrored about `SCREEN_WIDTH // 2`, with the tower in the gap:
  - left group x = `CITY_EDGE_MARGIN + i * BUILDING_SPACING` for i = 0..3 → 30, 110, 190, 270;
  - right group x = `SCREEN_WIDTH - CITY_EDGE_MARGIN - width - (3 - i) * BUILDING_SPACING` for
    i = 0..3 → 470, 550, 630, 710;
  - `self.buildings` is in left-to-right order: `[30, 110, 190, 270, 470, 550, 630, 710]`;
  - y = `GROUND_Y - BUILDING_TYPES[type]["height"]`, which is 540, the same as today.
  Building type choice, count (`starting_buildings_count = 8`) and size do not change.
- **Launcher tower** (`entities/base.py`, `DefensiveBase`):
  - `position` is the muzzle, the top centre of the barrel: `(LAUNCHER_X, LAUNCHER_Y)` = `(400, 514)`.
  - `width = LAUNCHER_WIDTH` (60), `height = LAUNCHER_HEIGHT` (50),
    `render_offset_x = -LAUNCHER_WIDTH // 2` (-30), `render_offset_y = LAUNCHER_BARREL_HEIGHT` (16).
    `get_bounds()` keeps its formula and now returns the tower body `Rect(370, 530, 60, 50)`, which
    stands on the ground (`bottom == GROUND_Y`).
  - New `barrel_rect()` returns `Rect(396, 514, 8, 16)`: `LAUNCHER_BARREL_WIDTH` wide,
    `LAUNCHER_BARREL_HEIGHT` tall, centred on `LAUNCHER_X`, top at `LAUNCHER_Y`, bottom on the body's top.
  - `draw_base()` draws the body, then the barrel in the same colour as the body (`active_color`, or
    `inactive_color` when offline), then the reload bar. The old tube drawing (the
    `COLOR_DARK_BLUE` rect worked out from `position.y - 10`) is removed. The signature and
    defaults stay the same. The existing offline-outline code is left as it is.
  - `reload_progress()` and `cooldown_bar_rects()` stay as they are. The bar keeps 008's rule
    (`COOLDOWN_BAR_GAP` below the body, the body's width), so it now sits in the ground strip
    at `Rect(370, 584, 60, 4)`, like a status light on the tower's footing.
  - Docstrings no longer say "top-left".
- **Defense missiles** (`entities/missile.py`, `DefenseMissile`): start at `(LAUNCHER_X, LAUNCHER_Y)`.
  The constructor signature `DefenseMissile(target_point)` stays the same. Flight, speed, snapping
  and detonation do not change.
- **Constants** (`game/constants.py`): add the names listed in Touch points. Remove
  `LAUNCHER_X_OFFSET` and `LAUNCHER_Y_OFFSET` and leave no alias. The "Launcher position
  (top-left corner)" comment goes.
- **Docs.** In `README.md` "Gameplay", replace "Your launcher sits in the top-left corner of the
  screen." with a sentence saying the launcher tower stands on the ground at the bottom centre,
  between the two halves of the city, and missiles rise from it. Keep the reload-bar sentence. In
  `GAME_DESIGN.md`, update only the lines that say the launcher is top-left: §4.1 DefenseMissile
  position/velocity, §4.2 position and "Stationary launcher at top-left", §10 "Top launcher",
  §13 "Can launch defense missiles from top-left launcher".
- **Tests.** Add `tests/test_bottom_launcher.py`. Edit existing tests only as the table in
  criterion 14 allows.

## Out of scope
- Damage to the tower: incoming missiles or explosions knocking it out (GAME_DESIGN §4.2). For now
  incoming missiles pass through it, and nothing sets `is_active = False`.
- The offline red outline. It is drawn before the body fill and painted over, so it never shows.
  That is an existing quirk, left for whichever job adds tower damage.
- Incoming missiles exploding on the ground strip. Missiles that miss still fly off the bottom.
- Limiting where the player can aim. Clicks below the muzzle (y > 514, e.g. just above a
  building) still fire, and the missile flies sideways or slightly down. This keeps last-moment
  intercepts over the rooftops possible.
- Rotating the barrel toward the cursor, muzzle flash, smoke trails, sound.
- More than one launcher, ammo counts, or launcher choice per click.
- Changing building size, type, health, or how incoming missiles pick targets.
- Removing or fixing the unused `MainGame.spawn_new_building()` or `systems/collision.py`.
- Applying screen shake to the ground or tower. `draw()` still works out a shake offset and never
  applies it.
- Changing the start, pause or game-over screens. They still draw no ground or tower.
- Editing `.claude/agents/*.md`.

## Acceptance criteria
Tests patch `systems.score.CONFIG_PATH` to a file under `tmp_path` before building any `MainGame`
(the `main_game` fixture already does this). Terms:
- `FIRE` means `{"fire_missile": (400, 300)}`.
- A **bare base** is a `DefensiveBase()` built directly, with no game.
- **Surface draw** means: make a `pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))`, fill it with
  `COLOR_BLACK`, call `base.draw_base(surface)`, and read pixels with `surface.get_at((x, y))[:3]`.
- A **game frame** means `main_game.draw()` and then reading `main_game.screen`.

1. [test] **Constants.** `GROUND_HEIGHT == 20`, `GROUND_Y == SCREEN_HEIGHT - GROUND_HEIGHT == 580`,
   `LAUNCHER_WIDTH == 60`, `LAUNCHER_HEIGHT == 50`, `LAUNCHER_BARREL_WIDTH == 8`,
   `LAUNCHER_BARREL_HEIGHT == 16`, `LAUNCHER_X == SCREEN_WIDTH // 2 == 400`,
   `LAUNCHER_Y == GROUND_Y - LAUNCHER_HEIGHT - LAUNCHER_BARREL_HEIGHT == 514`,
   `CITY_EDGE_MARGIN == 30`, `BUILDING_SPACING == 80`. All are ints. `COLOR_GROUND` is a 3-tuple of
   ints in 0–255 that differs from `COLOR_BLUE`, `COLOR_DARK_BLUE`, `COLOR_GRAY`, `COLOR_WHITE`,
   `COLOR_BLACK`, `COLOR_ORANGE` and `COLOR_YELLOW`. `game.constants` has no attribute
   `LAUNCHER_X_OFFSET` or `LAUNCHER_Y_OFFSET`.
2. [test] **Tower geometry.** On a bare base: `position == Vector2(400, 514)`;
   `get_bounds() == Rect(370, 530, 60, 50)`, with `bottom == GROUND_Y` and `centerx == LAUNCHER_X`;
   `barrel_rect() == Rect(396, 514, 8, 16)`, with `barrel_rect().bottom == get_bounds().top` and
   `barrel_rect().midtop == (400, 514)`. Both rects lie inside `Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)`.
3. [test] **Reload bar sits in the ground strip.** On a bare base,
   `cooldown_bar_rects()[0] == Rect(370, 584, 60, 4)`. `track.top >= GROUND_Y`,
   `track.bottom <= SCREEN_HEIGHT`, and the track does not `colliderect` `get_bounds()`.
4. [test] **City layout.** After `main_game.start_game()`, the building x positions in list order
   are exactly `[30, 110, 190, 270, 470, 550, 630, 710]` and every building's y is `540`. Each
   building's `get_bounds()` bottom is `GROUND_Y`. No building's bounds `colliderect` the tower body
   or barrel. The gap between buildings and tower is at least 40 px on each side: every building
   has `right <= 330` or `left >= 470`. The layout is mirrored: for i in 0..7,
   `buildings[i].x + buildings[i].width + buildings[7 - i].x == SCREEN_WIDTH`. Calling
   `start_game()` a second time gives the same positions.
5. [test] **Missiles start at the muzzle.** `DefenseMissile(Vector2(400, 300)).position ==
   Vector2(LAUNCHER_X, LAUNCHER_Y)`, and its velocity is `Vector2(0, -DEFENSE_MISSILE_SPEED)`
   (straight up). Through the game, after `main_game.handle_actions(FIRE)` the one missile in
   `defense_missiles` has `position == main_game.base.position`.
6. [test] **Missiles rise toward targets above the tower.** Parametrise the target over
   `(400, 300)`, `(50, 50)`, `(750, 50)`, `(100, 500)` and `(700, 513)`. For each,
   `velocity.y < 0`. Step `update(DT_DEFAULT)` until `reached_target`, at most 200 steps. Every step,
   `position.y` is less than or equal to the previous step's, and x and y stay inside the screen.
   The missile ends exactly on the target.
7. [test] **Flight time.** A `DefenseMissile` aimed at `(400, 300)` has not reached its target
   after 33 updates of `DT_DEFAULT` and has after the 34th (214 px at 380 px/s). Through the game:
   fire `(400, 300)` with `main_game.spawn_defense_missile`. After 33 `update(DT_DEFAULT)` calls,
   `explosions == []`. After the 34th, there is one player explosion at `Vector2(400, 300)`.
8. [test] **Tower pixels (bare surface).** Bare base, `reset()`, surface draw:
   - `(400, 555)` (body) and `(400, 520)` (barrel) are `COLOR_WHITE`;
   - `(400, 512)` (just above the muzzle), `(390, 520)` (beside the barrel), `(369, 555)` and
     `(430, 555)` (just outside the body) are `COLOR_BLACK`;
   - `(370, 585)` and `(429, 585)` are `COOLDOWN_BAR_READY_COLOR`, and `(400, 582)` (the gap) is
     `COLOR_BLACK`.
   With `is_active = False`, surface draw gives `COLOR_GRAY` at both `(400, 555)` and `(400, 520)`,
   so the barrel follows the body colour.
9. [test] **Ground and tower in the game frame.** After a game frame from `main_game`:
   `(5, 590)`, `(795, 590)`, `(400, 598)` and `(400, 582)` are `COLOR_GROUND`. `(5, 578)` is not
   `COLOR_GROUND`. `(400, 555)` and `(400, 520)` are `COLOR_WHITE`. `(375, 585)` is
   `COOLDOWN_BAR_READY_COLOR`. `(60, 560)` and `(740, 560)` are `COLOR_GRAY` (a building in each half).
10. [test] **Bar still works in the game frame.** Using `main_game`: `handle_actions(FIRE)`,
    `update(0.75)`, game frame: `(375, 585)` is `COOLDOWN_BAR_FILL_COLOR` and `(415, 585)` is
    `COOLDOWN_BAR_TRACK_COLOR`. Then `update(1.0)`, game frame: both are `COOLDOWN_BAR_READY_COLOR`.
11. [test] **Rising missile is drawn above the tower.** Using `main_game`: `handle_actions(FIRE)`,
    17 × `update(DT_DEFAULT)`, game frame. The missile is at about `(400, 406)`, and that pixel is
    `COLOR_YELLOW`.
12. [test] **Not on menu screens.** On a start-screen game (`MainGame()` left in `STATE_START`),
    `draw_start_screen()` leaves `(5, 590)` not `COLOR_GROUND` and `(400, 555)` not `COLOR_WHITE`.
    The same holds after setting `state = STATE_PAUSED` and calling `draw_start_screen()` again.
13. [test] **No top-left leftovers.** The source of `entities.base`, `entities.missile` and
    `systems.game_loop` contains neither `LAUNCHER_X_OFFSET` nor `LAUNCHER_Y_OFFSET`, and the
    source of `entities.base` does not contain `top-left`.
14. [test] **Existing tests, edited only where launcher or city geometry is hard-coded.** No
    other test file or test changes:

    | File / test | Change |
    |---|---|
    | `test_missiles_explode.py` imports and `LAUNCHER` | `LAUNCHER_X_OFFSET`/`LAUNCHER_Y_OFFSET` → `LAUNCHER_X`/`LAUNCHER_Y` |
    | `test_straight_flight` | loop `range(1, 34)` instead of `range(1, 75)` |
    | `test_arrival_on_step_75_and_stays` | 33 updates not arrived, 34th arrives (rename to `..._step_34_...` allowed) |
    | `test_zero_length_shot` | use `LAUNCHER_X`, `LAUNCHER_Y` |
    | `test_detonation_through_game` | 33 / 34 instead of 74 / 75 |
    | `test_no_contact_detonation` | parked incoming at `(400, 420)`; sanity distance check `> EXPLOSION_MAX_RADIUS` instead of `> 200`; 33 / 34 instead of 74 / 75 |
    | `test_end_to_end_intercept` | loop `range(1, 42)`, assert `34 <= killed_on <= 41`; docstring numbers updated |
    | `test_missile_drawn_where_it_is` | 17 updates instead of 37 |
    | `test_reset_cooldown.py` import and `test_start_game_keeps_the_same_launcher` | `LAUNCHER_X`/`LAUNCHER_Y`; "about 1.24 s" in the criterion 6 docstring → "about 0.57 s" |
    | `test_cooldown_indicator.py` | `TRACK = Rect(370, 584, 60, 4)`, `ROW = 585`; in `test_bar_position` the expected rect is the same; x samples `5, 20, 34, 35, 50, 64` → `370, 385, 399, 400, 415, 429`; `(4, ROW)`/`(65, ROW)` → `(369, ROW)`/`(430, ROW)`; gap pixel `(30, 32)` → `(400, 582)`; body pixel `(30, 15)` → `(400, 555)`; game-frame pixels `(10, ROW)`/`(50, ROW)` → `(375, ROW)`/`(415, ROW)` |
    | `test_buildings_game_over.py::test_spawns_target_standing_buildings_only` | `assert target_x == 710` instead of `590` |

    The full suite passes with the README command, and the real `config.json` is byte-for-byte unchanged.
15. [visual] **Opening frame.** Using `main_game`, `random.seed(0)` before `start_game()`, game
    frame. There is a `COLOR_GROUND` strip along the bottom 20 px. A white tower stands on it at the
    centre, 60 px wide and 50 px tall, with a thin barrel on top reaching above the rooftops. Four
    grey buildings stand each side of it, with clear sky between the city halves and the tower. Under
    the tower, inside the ground strip, the reload bar is all `COLOR_YELLOW`. The HUD score at top
    right is unchanged, and nothing remains in the top-left corner.
16. [visual] **Firing frame.** The same game: `handle_actions({"fire_missile": (150, 120)})`,
    20 × `update(DT_DEFAULT)` + `check_collisions()`, game frame. A yellow missile is up and to the
    left of the barrel, on the line from the muzzle to (150, 120). The reload bar is part orange
    (`COLOR_ORANGE`) from the left, with the rest `COLOR_DARK_BLUE`, and readable against the ground.

## Touch points
- `game/constants.py`:
  - Colours: `COLOR_GROUND = (70, 90, 50)`, a dark olive ground.
  - New "Ground" section: `GROUND_HEIGHT = 20`, `GROUND_Y = SCREEN_HEIGHT - GROUND_HEIGHT`.
  - Replace the "Launcher position (top-left corner)" block with: `LAUNCHER_WIDTH = 60`,
    `LAUNCHER_HEIGHT = 50`, `LAUNCHER_BARREL_WIDTH = 8`, `LAUNCHER_BARREL_HEIGHT = 16`,
    `LAUNCHER_X = SCREEN_WIDTH // 2`, `LAUNCHER_Y = GROUND_Y - LAUNCHER_HEIGHT - LAUNCHER_BARREL_HEIGHT`.
    Remove `LAUNCHER_X_OFFSET` and `LAUNCHER_Y_OFFSET`.
  - City layout (near building settings): `CITY_EDGE_MARGIN = 30`, `BUILDING_SPACING = 80`.
  - Every name must be defined after the names it uses.
- `entities/base.py`: `DefensiveBase.__init__` (position, size, offsets from constants), new
  `barrel_rect()`, `draw_base()` (barrel replaces the tube), and the class and `__init__` docstrings.
- `entities/missile.py`: `DefenseMissile.__init__` starting point.
- `systems/game_loop.py`: `MainGame.start_game()` building layout; `MainGame.draw()` ground fill.
- `README.md` "Gameplay"; `GAME_DESIGN.md` §4.1, §4.2, §10, §13 launcher lines.
- `tests/test_bottom_launcher.py` (new), plus the edits in criterion 14.

Expected diff: about 50–70 lines of game code, constants and docs, about 150–200 lines of new
tests, and about 30 changed lines in existing tests. Parametrise criterion 6. Reuse the
surface-draw and `_px` helper pattern from `tests/test_cooldown_indicator.py`.

## Notes for reviewers
- **code:**
  - One source of truth: tower, barrel and muzzle come from the `LAUNCHER_*` and `GROUND_*`
    constants. Missile start, body bounds, barrel and building positions must not repeat raw
    numbers like 400, 514 or 580.
  - `DefensiveBase.position` now means the muzzle (the launch point), not a point inside the body.
    `DefenseMissile` must start at the same point. Criterion 5 checks this against `base.position`.
  - `cooldown_bar_rects()` and `reload_progress()` should be untouched. The bar moves only because
    `get_bounds()` moved.
  - The building layout must be worked out from the constants and the building width, not
    written as a literal list of x values. It must stay mirrored (criterion 4).
  - Check that the criterion 14 edits are limited to the table: no assertions loosened beyond
    what the new geometry needs, and no tests deleted.
- **security:** No new file, network or config I/O. Tests patch `CONFIG_PATH` before building a
  `MainGame`. Surface-draw and geometry tests need no `MainGame`.
- **ux:**
  - Shots now rise from the ground, so time to target depends on height. A click at (400, 300)
    lands in about 0.57 s instead of 1.24 s. Targets near the top corners take about 1.5 s.
    Incoming missiles near the rooftops are now the quickest to reach. Check this still feels fair.
  - Clicks below the muzzle still fire (see Out of scope). Confirm that nothing looks broken
    when a missile flies sideways toward a low target.
  - The reload bar is now under the tower, in the ground strip near the city, where the player's
    eyes already are. Yellow still means "ready".
- **ui:**
  - Check frames 15 and 16. The tower must read as a launcher standing on the ground, not as
    another building. White body and barrel against grey buildings and blue sky, with clear
    space (40 px or more) between it and the nearest building on each side.
  - The reload bar sits on `COLOR_GROUND`. Check that the `COLOR_DARK_BLUE` track and the orange
    and yellow fill are all easy to tell apart from the ground. If the track is too faint, say so.
    Changing `COLOR_GROUND` is in scope, but the bar colours are not.
  - The city is now centred and symmetric (30 px margins both sides). Before, it ran x 30–650.
  - `.claude/agents/ui-reviewer.md` still describes the launcher as top-left. Judge this job
    against this spec, not that line.
