# 004-game-states: Start screen, ESC pause/resume, SPACE restart, game-time spawns

## Problem
The state flow doesn't work. `start_game_loop()` forces `STATE_PLAYING` on launch, so the
start screen never shows. ESC pauses, but nothing ever emits `"resume"`, so a paused game
can't be resumed. Pressing SPACE during play switches to `STATE_START` and runs a loop that
removes standing buildings from `self.buildings` while iterating over it. On the game-over
screen, SPACE rebuilds the city but leaves the state at `STATE_GAME_OVER`, so play never
restarts. Enemy spawns are timed with `pygame.time.get_ticks()` (wall clock). Time spent
paused therefore counts towards the next spawn, and after resuming one spawns at once. The
start/pause screen text also overlaps and lists the wrong keys.

## Scope
- **Action names.** In `InputSystem.handle_events()`, ESC now emits `"toggle_pause"` and
  SPACE emits `"start"`, replacing `"pause"` and `"start_pause"`. `"quit"` and
  `"fire_missile"` don't change.
- **One place for transitions.** Add a new `MainGame.handle_actions(actions)`, which takes
  the dict from `handle_events()`. It reads the state at the start of the call and makes at
  most one state change per call:
  | State at call start | Action | Result |
  |---|---|---|
  | `STATE_START` | `"start"` | `start_game()`, state → `STATE_PLAYING`, `self.timer.reset()` |
  | `STATE_PLAYING` | `"toggle_pause"` | state → `STATE_PAUSED` |
  | `STATE_PAUSED` | `"toggle_pause"` | state → `STATE_PLAYING`, `self.timer.reset()`; nothing else changes |
  | `STATE_GAME_OVER` | `"start"` | `start_game()`, state → `STATE_PLAYING`, `self.timer.reset()` |
  | anything else | — | no change (e.g. SPACE while playing or paused, ESC on the start or game-over screen) |

  `"fire_missile"` calls `spawn_defense_missile(pos)` only when the state is
  `STATE_PLAYING` both at the start and at the end of the call. `handle_actions()` never
  calls `save_high_score()` and never switches to `STATE_GAME_OVER`; that stays in
  `check_game_over()`.
- **Loop.** `start_game_loop()` stops setting `self.state = STATE_PLAYING` and stops calling
  `start_game()`. It runs in whatever state the game is in, which is `STATE_START` from
  `__init__` in real play. Each frame it keeps the `"quit"` check, calls
  `handle_actions(actions)`, then runs the existing playing frame or `draw_start_screen()`.
  Delete:
  - the SPACE-during-play branch that removes buildings;
  - the `"resume"` branch;
  - the old `"pause"` branch;
  - the inline game-over restart block.
- **Game-time spawns.** Spawns are timed on game time, which only advances in `update(dt)`.
  - `update()` spawns when `self.game_time - self.last_spawn_time >= current_interval`,
    then sets `self.last_spawn_time = self.game_time`. The interval formula doesn't change.
  - `start_game()` sets `self.last_spawn_time = 0.0` and also resets
    `self.shake_intensity = 0`.
  - `update()` and `start_game()` no longer call `pygame.time.get_ticks()`.
  - The test fixture's `last_spawn_time = float("inf")` still means "never spawn".
- **Start and pause screens.** Add a new `MainGame.menu_lines()` that returns a list of
  `(text, font_size, color, centre_y)` tuples for `STATE_START` and `STATE_PAUSED`.
  `draw_start_screen()` renders those lines centred at `x = SCREEN_WIDTH // 2`, replacing the
  current overlapping layout. The `STATE_GAME_OVER` branch doesn't change. Lines, top to
  bottom (H = `SCREEN_HEIGHT`):
  - START:
    - `"Missile Command Clone"` (48, `COLOR_WHITE`, H//2-120)
    - `"Defend the city!"` (36, `COLOR_GRAY`, H//2-80)
    - `f"High Score: {high_score:,}"` (36, `COLOR_YELLOW`, H//2-30)
    - the controls block
    - `"Press SPACE to Start"` (48, `COLOR_YELLOW`, H//2+190)
  - PAUSED:
    - `"PAUSED"` (48, `COLOR_WHITE`, H//2-120)
    - `f"Score: {score:,}"` (36, `COLOR_YELLOW`, H//2-30)
    - the controls block
    - `"Press ESC to Resume"` (48, `COLOR_YELLOW`, H//2+190)
  - The controls block is four lines, all 36 and `COLOR_WHITE`, at H//2+20, +50, +80 and
    +110:
    - `"Controls:"`
    - `"Mouse Click: Launch defense missile"`
    - `"SPACE: Start / Restart"`
    - `"ESC: Pause / Resume"`
- **README.** Change the Controls table to:
  - Left Click: launch a missile;
  - SPACE (start screen): Start;
  - ESC: Pause / Resume;
  - SPACE (Game Over screen): Restart.
- **Tests.** Add a new file `tests/test_game_states.py`.

## Out of scope
- Drawing the frozen game frame behind the pause text (backlog "Pause overlay").
- Scoring (backlog item 5). `handle_score_updates()` is dead code. It still calls
  `get_ticks()` and is left alone; the scoring job owns it.
- Click to start, ESC on the start screen to quit, a "back to menu" action, and the start
  screen's "score reset option" from GAME_DESIGN.md.
- Resetting the launcher (`DefensiveBase`) cooldown on restart, and any other change to the
  game-over screen layout.
- Updating `GAME_DESIGN.md`.

## Acceptance criteria
Tests use the `main_game` fixture: `STATE_PLAYING`, 8 buildings, no spawns, `CONFIG_PATH`
under `tmp_path`. They also use `random.seed(0)` and `DT_DEFAULT`, unless a criterion says
otherwise. A **fresh game** means: monkeypatch `systems.score.CONFIG_PATH` to
`tmp_path / "config.json"`, then build `MainGame()` without calling `start_game()`. Before
any test calls `handle_actions` with `"fire_missile"`, it sets `game.base.cooldown_time = 0`.

1. [test] **Key mapping:** post a `KEYDOWN` event for each key and call
   `game.input_system.handle_events()`.
   - `K_ESCAPE` returns `{"toggle_pause": True}`.
   - `K_SPACE` returns `{"start": True}`.
   - A left `MOUSEBUTTONDOWN` at (400, 300) returns `{"fire_missile": (400, 300)}`.
2. [test] **Opens on the start screen:** take a fresh game and monkeypatch `handle_events`
   with a fake that returns `{}` for calls 1–4 and `{"quit": True}` on call 5. Run
   `start_game_loop()`. It returns with:
   - `game.state == STATE_START`;
   - `game.buildings == []` and `game.incoming_missiles == []`;
   - `game.game_time == 0.0`.
3. [test] **SPACE starts play:** a fresh game's `handle_actions({"start": True})` gives:
   - `STATE_PLAYING`;
   - `len(game.buildings) == 8`, every building at `health_max`;
   - `game.last_spawn_time == 0.0` and `game.game_time == 0.0`.
4. [test] **The start screen ignores other input:** on a fresh game, each of these leaves the
   state `STATE_START` and `game.defense_missiles == []`:
   - `handle_actions({"toggle_pause": True})`;
   - `handle_actions({"fire_missile": (400, 300)})`.
5. [test] **ESC pauses and resumes without losing anything:**
   - Record a snapshot:
     - `game.buildings`, as a list of object identities with `health_current`;
     - `game.game_time`;
     - `game.score_system.score`;
     - the position of one stationary planted `IncomingMissile`.
   - `handle_actions({"toggle_pause": True})` gives `STATE_PAUSED`.
   - A second call gives `STATE_PLAYING`.
   - The snapshot is identical after both calls.
6. [test] **Paused input is ignored:** while `STATE_PAUSED`:
   - `handle_actions({"start": True})` leaves `STATE_PAUSED` and 8 buildings;
   - `handle_actions({"fire_missile": (400, 300)})` adds no defense missile.
7. [test] **SPACE during play does nothing (regression):** in `STATE_PLAYING`,
   `handle_actions({"start": True})`:
   - leaves `STATE_PLAYING`;
   - keeps `len(game.buildings) == 8`, with the same building objects in the same order.
8. [test] **Firing still works in play:** in `STATE_PLAYING`,
   `handle_actions({"fire_missile": (400, 300)})` adds exactly one defense missile.
   `handle_actions({"toggle_pause": True, "fire_missile": (400, 300)})` pauses and adds no
   missile.
9. [test] **SPACE restarts from game over:**
   - Set `game.score_system.score = 120` and wrap `save_high_score` with a counter.
   - Mark all buildings `is_destroyed = True`, then call `check_collisions()` and
     `check_game_over()`. The state is `STATE_GAME_OVER` and the save count is 1.
   - Then call `handle_actions({"start": True})`. Afterwards:
     - `game.state == STATE_PLAYING`;
     - 8 buildings, all at `health_max`;
     - `game.score_system.score == 0` and `game.score_system.high_score == 120`;
     - `game.game_time == 0.0` and `game.last_spawn_time == 0.0`;
     - `game.shake_intensity == 0`;
     - `incoming_missiles`, `defense_missiles` and `explosions` are all empty;
     - the save count is still 1.
   - A following `check_game_over()` leaves `STATE_PLAYING`.
10. [test] **ESC on game over does nothing:** in `STATE_GAME_OVER`,
    `handle_actions({"toggle_pause": True})` leaves `STATE_GAME_OVER`.
11. [test] **Spawns run on game time:**
    - Monkeypatch `pygame.time.get_ticks` to raise.
    - Set `game.last_spawn_time = 0.0`.
    - Call `update(DT_DEFAULT)` 180 times. `len(game.incoming_missiles) == 0`. The
      interval at t = 3.0 s is 3.33 s.
    - 30 more calls (210 in total) give exactly 1 incoming missile. The first spawn is near
      t ≈ 3.32 s.
    - Nothing raises.
12. [test] **Pausing doesn't advance game time or burst spawns:**
    - Monkeypatch `utils.timer.time` with a fake module whose `time()` returns a controlled
      clock.
    - Call `game.timer.reset()` and set `game.last_spawn_time = 0.0`.
    - Fake `handle_events`. Every call except the last advances the clock by 1/60 s. Then:
      - calls 1–30 return `{}`;
      - call 31 returns `{"toggle_pause": True}`;
      - call 32 also advances the clock by 60 s and returns `{}`;
      - call 33 returns `{"toggle_pause": True}`;
      - calls 34–40 return `{}`;
      - call 41 returns `{"quit": True}`.
    - Run `start_game_loop()`. Afterwards:
      - `game.state == STATE_PLAYING`;
      - `game.game_time == pytest.approx(37 / 60, abs=1e-6)`, from 30 + 7 frames. The resume
        frame has dt 0. Without `timer.reset()` the 60 s jump would add the 0.16 s clamp;
      - `game.incoming_missiles == []`.
13. [test] **Menu text:**
    - A fresh game with `config.json` containing `{"high_score": 250}` has
      `menu_lines()` texts that include `"High Score: 250"` and `"Press SPACE to Start"`.
    - In `STATE_PAUSED` with `score = 1234`, the texts include `"PAUSED"`, `"Score: 1,234"`
      and `"Press ESC to Resume"`.
    - In both states:
      - no text contains `"Start/Pause"`;
      - the `centre_y` values strictly increase, with consecutive gaps of at least 30;
      - every `centre_y` is within `0..SCREEN_HEIGHT`.
    - `draw_start_screen()` doesn't raise for `STATE_START`, `STATE_PAUSED` or
      `STATE_GAME_OVER`.
14. [test] All existing tests pass unchanged, including the 003 criterion 14 real-loop test.
    That test still reaches `STATE_GAME_OVER` with one save, because the loop no longer
    forces a fresh game. The full suite passes with the README command, and the real
    `config.json` is byte-for-byte unchanged.
15. [visual] **Start screen:** render a fresh game's `draw_start_screen()` with high score
    250 and save the frame. It shows these lines, top to bottom, all horizontally centred,
    none overlapping:
    - the title, in `COLOR_WHITE`;
    - "Defend the city!", in `COLOR_GRAY`;
    - "High Score: 250", in `COLOR_YELLOW`;
    - the four control lines, in `COLOR_WHITE`;
    - "Press SPACE to Start", in `COLOR_YELLOW`.
16. [visual] **Pause screen:** start a game, pause it with score 1234, then render
    `draw_start_screen()`. The frame shows these lines, centred and not overlapping:
    - "PAUSED";
    - "Score: 1,234", in `COLOR_YELLOW`;
    - the four control lines;
    - "Press ESC to Resume", in `COLOR_YELLOW`.
17. [visual] **First playing frame:** after `handle_actions({"start": True})` on a fresh game,
    `draw()` shows:
    - 8 `COLOR_GRAY` buildings along the bottom;
    - the launcher top-left;
    - `"SCORE: 0"` top-right;
    - no missiles.

## Touch points
- `systems/input_system.py`, `handle_events()`: rename the ESC and SPACE actions to
  `"toggle_pause"` and `"start"`.
- `systems/game_loop.py`:
  - New `handle_actions(actions)` and `menu_lines()`.
  - `start_game()`: set `last_spawn_time = 0.0`, reset `shake_intensity`, and drop
    `get_ticks`.
  - `update()`: the spawn check uses `game_time`.
  - `start_game_loop()`: no forced state or `start_game()`; call `handle_actions()`; delete
    the old branches.
  - `draw_start_screen()`: render `menu_lines()` for START and PAUSED.
- `README.md`: the Controls table.
- `tests/test_game_states.py` (new).
- `game/constants.py`: no new constants. Use the existing `STATE_*`, `COLOR_WHITE`,
  `COLOR_GRAY`, `COLOR_YELLOW`, `BASE_SPAWN_INTERVAL`, `MIN_SPAWN_INTERVAL` and `DT_DEFAULT`.

Expected diff: about 90 lines of game code and at most about 200 lines of tests. Jobs 002 and
003 both escalated on size (003 had 422 lines), so the total must stay under 400. Use shared
helpers (a fresh-game fixture, a fake event sequence builder, a save counter) and
parametrise the "no change" cases (criteria 4, 6, 7 and 10).

## Notes for reviewers
- **code:**
  - `handle_actions()` must be the only place that changes state on input. Grep for any
    leftover `"pause"`, `"start_pause"` or `"resume"` strings, and for any
    `self.state = STATE_PLAYING` outside `handle_actions()`.
  - Transitions must be decided from the state at the start of the call, so a single call
    can't pause and then resume. A call also can't start and then pause.
  - `get_ticks` must not appear in `update()` or `start_game()`. The only remaining use
    should be the dead `handle_score_updates()`.
  - `timer.reset()` must run on every entry to `STATE_PLAYING` (start, resume and restart),
    or the first frame after a long pause gets the 0.16 s clamp.
  - The deleted buildings branch mutated a list while iterating over it. Confirm it's gone,
    not just made unreachable.
  - Criteria 2 and 12 drive the real loop. Check that both fakes quit on a fixed call number,
    so they can't hang.
- **security:** No new file or network I/O. `save_high_score()` must still be called only
  from `check_game_over()`. A restart must not save again (criterion 9). Tests must not
  touch the real `config.json`. Fresh games patch `CONFIG_PATH` before construction. The
  `utils.timer.time` monkeypatch must be scoped to the test.
- **ux:**
  - SPACE is ignored while playing and while paused, so ESC is the only pause key. That
    matches the feature, but GAME_DESIGN.md §6 calls SPACE a "Start/Pause toggle". Flag it
    if SPACE-to-resume feels missing.
  - Clicks on the start, pause and game-over screens do nothing.
  - After a restart, the launcher keeps whatever cooldown it had (out of scope). Note it if
    it's noticeable.
- **ui:** Check frames 15–17.
  - Nothing on the start or pause screen should overlap. Today "Score" collides with the
    subtitle and "High Score" with "Controls:".
  - The prompt line should be the most prominent element after the title (48 pt,
    `COLOR_YELLOW`).
  - `COLOR_GRAY` on the dimmed dark-blue background is low contrast. It's kept for the
    subtitle only; say so if it's unreadable.
