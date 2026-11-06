APPROVE

**Reason:** Wave counter derived from game_time and shown left of the score; all 14 criteria met, 308 tests pass, the diff stays in scope, all four reviews PASS.

## Rationale
- **Gates:** build.md says `STATUS: READY`. All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. Their findings are all nits and none is a **should**. The reviewers agree.
- **Criteria 1-11:** each one has a matching test in `tests/test_wave_counter.py` and the tests check what the spec says. They cover the boundary values with `type(w) is int`, the 0.5 s stepping across 30 s and 60 s, the text with thousands separators, the absence of any `wave` attribute and side effects, the pause and game-over freezes (using a local copy of the fake-clock helper scoped by monkeypatch), the reset to wave 1 on restart, the layout and pixels, and the wave moving left with a longer score.
- **Criterion 12:** I ran the README command in the worktree and got `308 passed`. No existing test file is in the diff. The sha256 of `config.json` was the same before and after the run.
- **Criteria 13-14 (visual):** the builder rendered both frames and the UI reviewer rendered them again on its own. Both report a white `WAVE` and a yellow `SCORE` on one row, a 24 px gap, the score unchanged at a 10 px margin, and no clipping or overlap for long values.
- **Code:** `current_wave()` is `int(self.game_time // WAVE_DURATION) + 1`. There is no new state and no wall clock. `draw_hud()` places the wave from the measured `score_rect.left`. `draw()` only swaps its four old HUD lines for `self.draw_hud()`. `update()`, `start_game()`, `spawn_defense_missile()`, `entities/base.py` and `systems/sound.py` are untouched.
- **Scope and risk:** 4 files changed: README (1 Features bullet), constants (3 constants in `# Scoring`), `game_loop.py` (+34/-4) and the new test file. Nothing is deleted, there are no new dependencies and the `config.json` format is unchanged. `git merge-tree` against main is clean. The edits keep out of the methods and README line that parallel job 013 changes, so the two should merge without conflict.
