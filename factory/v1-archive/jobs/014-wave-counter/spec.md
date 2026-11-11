# 014-wave-counter: Wave number in the HUD, up by one every 30 seconds of play

## Problem
During play the HUD shows only the score. Nothing tells the player how far into a run they
are or marks their progress. GAME_DESIGN.md §9 describes waves, but the game has no wave
idea at all. The player wants a wave counter that starts at 1, goes up by one for every
30 seconds of play, and is shown in the HUD next to the score.

## Scope
- **Wave number** (`systems/game_loop.py`, `MainGame`):
  - New method `current_wave()` returns `int(self.game_time // WAVE_DURATION) + 1` as an
    `int`. So 0 s up to but not including 30 s is wave 1, 30 s up to 60 s is wave 2, and so on.
  - The wave is **derived** from the existing `self.game_time` every time it is asked for.
    There is no new timer, accumulator or wave attribute. `update()` is not changed at all.
  - Because `game_time` only goes up in `update()`, which only runs in `STATE_PLAYING`, time
    spent paused, on the start screen or on the game over screen doesn't count. Pausing
    freezes the wave.
  - `start_game()` already sets `game_time = 0.0`, so every new game (including a restart
    with SPACE after game over) starts at wave 1. `start_game()` is not changed.
- **HUD text**: new method `MainGame.hud_wave_text()` returns `f"WAVE: {self.current_wave():,}"`,
  for example `"WAVE: 3"` or `"WAVE: 1,001"`.
- **HUD drawing**:
  - Move the score-drawing lines at the end of `draw()` into a new method
    `MainGame.draw_hud()`, which `draw()` calls in the same place (after explosions, before
    `pygame.display.flip()`).
  - `draw_hud()` renders both lines with one `pygame.font.Font(None, 36)`:
    - the score exactly as today: `hud_score_text()` in `COLOR_YELLOW`, with its rect's
      `topright == (SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN)`;
    - the wave: `hud_wave_text()` in `HUD_WAVE_COLOR`, on the same row to the left of the
      score. Its rect has `top == HUD_MARGIN` and `right == score_rect.left - HUD_WAVE_GAP`.
  - `draw_hud()` blits both surfaces onto `self.screen` and returns
    `(score_rect, wave_rect)` so tests can check the layout. It doesn't call `flip()`.
  - The wave is positioned from the score rect's measured `left`, never from a hard-coded
    width, so it moves left as the score gets longer.
  - The HUD is not shaken, as today.
- **Constants** (`game/constants.py`), in the `# Scoring` section next to `HUD_MARGIN`:
  - `WAVE_DURATION = 30.0`: seconds of play per wave.
  - `HUD_WAVE_COLOR = COLOR_WHITE`: wave text colour. It is different from the yellow score so
    the two read as separate items, and so tests can tell their pixels apart.
  - `HUD_WAVE_GAP = 24`: px between the right edge of the wave text and the left edge of the
    score text.
- **README**: one new bullet in the **Features** list, right after the "Score tracks missile
  hits…" bullet: "A wave counter next to the score goes up by one every 30 seconds of play".
  Don't edit the one-line Gameplay paragraph, because job 013 edits that line (see Notes).
- **Tests**: new file `tests/test_wave_counter.py`. No existing test is edited.

## Out of scope
- Any gameplay change tied to the wave: spawn rate, missile speed, number of enemies, new
  buildings or a per-wave score bonus. The spawn formula in `update()` stays as it is.
  Linking difficulty to waves is a possible follow-up.
- A "WAVE 2" banner, flash, sound or any other announcement when the wave changes.
- Showing the wave on the pause, start or game over screens, or in `menu_lines()`.
- Saving a best wave or anything else about waves to `config.json`.
- A countdown to the next wave or a progress bar.
- Any change to `update()`, `start_game()`, `spawn_defense_missile()` or `entities/base.py`.
  These belong to job 013.
- Editing GAME_DESIGN.md, and the unused `ScoreDisplay` class in `systems/score.py`.

## Acceptance criteria
Terms used below:
- `main_game` is the existing conftest fixture (playing, `CONFIG_PATH` patched to
  `tmp_path`, no random spawns).
- **Fake-clock loop** means the `_loop_with_fake_clock` pattern from `tests/test_scoring.py`
  criterion 9: monkeypatch `utils.timer.time` with a fake clock, and fake `handle_events` so
  that calls 1–10 each move the clock forward 1.0 s and return `{}`, and call 11 returns
  `{"quit": True}`. Then run `start_game_loop()`. Copy the helper into the new test file
  rather than importing it from `test_scoring.py`.
- **White pixels** in a region means pixels whose RGB is exactly `HUD_WAVE_COLOR`.

1. [test] **Constants.** `WAVE_DURATION == 30.0`, `HUD_WAVE_COLOR == COLOR_WHITE` and
   `HUD_WAVE_GAP == 24`.
2. [test] **Wave boundaries.** On `main_game`, set `game_time` directly (with no `update()`)
   and call `current_wave()`. The results are `0.0 → 1`, `29.99 → 1`, `30.0 → 2`,
   `59.99 → 2`, `60.0 → 3`, `299.99 → 10` and `300.0 → 11`. Every result is an `int`
   (`type(w) is int`).
3. [test] **Wave goes up through play.** On `main_game` right after the fixture,
   `current_wave() == 1`. After 59 calls of `update(0.5)` (`game_time == 29.5`), it is still
   1. One more `update(0.5)` (`game_time == 30.0`) makes it 2. 60 more calls make it 3.
   (Sums of 0.5 are exact in floating point, so there is no drift at the boundary.)
4. [test] **HUD text.** `hud_wave_text() == "WAVE: 1"` at start. With `game_time = 65.0` it is
   `"WAVE: 3"`, and with `game_time = 30000.0` it is `"WAVE: 1,001"`.
5. [test] **No wave bonus and no other side effects.** On `main_game`, set
   `game_time = 29.5` and `score_system.time_survived = 29.5`. One `update(1.0)` makes
   `current_wave() == 2` and raises `score_system.score` by exactly
   `SURVIVAL_POINTS_PER_SECOND` (1), the normal survival point. `defense_missiles`,
   `incoming_missiles` and `explosions` are still empty, and `base.can_fire()` is unchanged.
   `vars(game)` has no new key containing `"wave"` after the update. Calling
   `current_wave()` 100 times leaves `game_time` unchanged.
6. [test] **Pause and menus freeze the wave.** On `main_game`, set `game_time = 29.0`, call
   `handle_actions({"toggle_pause": True})` so `state == STATE_PAUSED`, then run the
   fake-clock loop (10 s of paused frames). Afterwards `game_time == 29.0` and
   `current_wave() == 1`. Resume with `handle_actions({"toggle_pause": True})`; one
   `update(DT_DEFAULT)` leaves `current_wave() == 1`. Repeat the paused-loop part with
   `state = STATE_GAME_OVER` and `game_time = 95.0`; the wave stays 4.
7. [test] **Restart goes back to wave 1.** On `main_game`, set `game_time = 95.0`
   (`current_wave() == 4`). Mark every building destroyed, then call `check_collisions()` and
   `check_game_over()` (`state == STATE_GAME_OVER`). `handle_actions({"start": True})` gives
   `current_wave() == 1` and `hud_wave_text() == "WAVE: 1"`.
8. [test] **HUD layout.** On `main_game`, `score_rect, wave_rect = game.draw_hud()`:
   - `score_rect.topright == (SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN)`;
   - `wave_rect.top == HUD_MARGIN` and `wave_rect.right == score_rect.left - HUD_WAVE_GAP`;
   - `wave_rect.width > 0`, and the two rects don't overlap (`not wave_rect.colliderect(score_rect)`).
   - Repeat with `score_system.score = HIGH_SCORE_MAX` and `game_time = 30000.0`: the same
     equalities hold and `wave_rect.left >= 0`, so the whole wave text is on screen.
9. [test] **HUD pixels.** On `main_game`, call `draw()`, then compute the rects by calling
   `draw_hud()` again:
   - `wave_rect` contains at least one white pixel;
   - the gap strip (columns `wave_rect.right` to `score_rect.left - 1`, rows `HUD_MARGIN` to
     `score_rect.bottom - 1`) contains no white pixels;
   - `score_rect` contains at least one pixel equal to `COLOR_YELLOW` and no white pixels.
10. [test] **HUD follows the wave.** On `main_game`, render `draw()` with `game_time = 10.0`
    and with `game_time = 35.0`, keeping `score_system.score` at 0 both times. The pixels in
    the region `(SCREEN_WIDTH - 300, 0, 300, 50)` differ between the two frames, and the
    score rect returned by `draw_hud()` is identical in both.
11. [test] **The wave moves left with the score.** With `game_time = 0.0`, `draw_hud()` at
    `score = 0` and at `score = 1234567` gives two wave rects with the same `width`. The
    second one's `right` is smaller by exactly the difference between the two score rects'
    widths.
12. [test] All existing tests pass unedited, including `tests/test_scoring.py` criteria 12
    and 13 (live HUD score, right-aligned and clear of the right margin). The full suite
    passes with the README command, and the real `config.json` is byte-for-byte unchanged.
13. [visual] **Mid-play HUD.** Start a game, run `update(0.5)` 130 times (`game_time == 65.0`,
    score 65) and render `draw()`. The top-right corner reads `WAVE: 3` in white, then a
    small gap, then `SCORE: 65` in yellow, all on one row with matching tops and the same
    font size. The score sits where it always has, about `HUD_MARGIN` px from the top and
    right edges. The white text is clearly legible against the light top of the sky
    gradient.
14. [visual] **Long values.** With `score = 123456789` and `game_time = 30000.0`, `draw()`
    shows `WAVE: 1,001` and `SCORE: 123,456,789` on one row, both fully visible, not
    overlapping and not clipped at either edge.

## Touch points
- `game/constants.py`: in the `# Scoring` section after `HUD_MARGIN`, add
  `WAVE_DURATION = 30.0`, `HUD_WAVE_COLOR = COLOR_WHITE` and `HUD_WAVE_GAP = 24`, each with a
  short comment.
- `systems/game_loop.py` (`MainGame`):
  - new `current_wave()`;
  - new `hud_wave_text()`, next to `hud_score_text()`;
  - new `draw_hud()`;
  - `draw()`: replace its last four HUD lines (font, render, rect, blit) with one
    `self.draw_hud()` call. Nothing else in `draw()` changes.
- `README.md`: one Features bullet.
- `tests/test_wave_counter.py` (new).

Expected diff: about 25 lines in `game_loop.py`, 3 constants, 1 README line, and 150–200
lines of tests.

## Notes for reviewers
- **code:**
  - There is one source of truth: `current_wave()` is computed from `game_time`. Check there
    is no `self.wave` attribute, no second timer, and no wall clock (`time.time()`,
    `pygame.time.get_ticks()`), any of which could drift from `game_time` or keep running
    while paused.
  - **Parallel job 013-rapid-fire-powerup** also reads `game_time` and edits
    `systems/game_loop.py`, but only in `update()`, `spawn_defense_missile()` and a new
    `rapid_fire_active()`. This job must stay out of those methods, and out of
    `entities/base.py` and `systems/sound.py`, so the two branches merge cleanly. Neither
    job depends on the other's code. Both only *read* `game_time`, which already exists
    on main.
  - 013 adds a sentence to the one-line README Gameplay paragraph. That is why this job's
    README change is a separate Features bullet: two edits to the same line would conflict.
    Constants go in the `# Scoring` section; 013 adds its constants by the launcher ones.
  - `draw_hud()` must keep the score's current position, colour and font exactly, so the
    existing `test_scoring.py` HUD tests pass without edits. The wave rect must be computed
    from the rendered score rect (`score_rect.left`), not from a fixed x.
  - `//` on floats: `30.0 // 30.0 == 1.0` and `60.0 // 30.0 == 2.0` exactly. Wrap the result
    in `int()` so the method returns an `int`, not `2.0`.
- **security:** No new file, network or config I/O. Nothing about waves is saved. Tests must
  patch `CONFIG_PATH` (the `main_game` fixture does) and keep the `utils.timer.time`
  monkeypatch scoped to the test.
- **ux:**
  - The wave goes up purely with time and changes nothing else yet, so it is a progress
    marker, not a difficulty step. If it feels pointless in play, flag it so a later job can
    tie the spawn rate to it.
  - The change from wave N to N+1 is silent. Check that the player still notices it during
    play. A banner or sound is a possible follow-up.
- **ui:** Check frames 13 and 14.
  - Both HUD items use the 36 pt default font. The wave is white and the score is yellow, on
    one row with matching tops, separated by `HUD_WAVE_GAP` (24 px).
  - The wave should read as a label next to the score, not crowd it. It must not overlap
    incoming missiles' entry area enough to hide threats.
  - Check that the white text is legible over the light top of the sky gradient.
