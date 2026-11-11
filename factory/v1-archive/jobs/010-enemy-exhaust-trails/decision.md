APPROVE

**Reason:** All 4 reviews PASS with nits only. 182/182 tests pass, and 251/251 after a trial merge onto current main (with 009 and 011). Scope is tight and there are no escalation triggers.

## Rationale
- **Gates:** build.md says `STATUS: READY`. The round-1 code, security, ui and ux reviews all say `VERDICT: PASS`. Their only findings are nits that the spec already accepts (grey tail is faint against the blue sky; trails draw over buildings in a missile's last frames). No **should** findings, and the reviewers agree.
- **Criteria:** Criteria 1-15 each map to a named test in `tests/test_enemy_exhaust_trails.py`, and I read each test against the spec's wording. They check:
  - samples are copies (`is` / `id` checks);
  - samples are recorded before the move;
  - the deque cap holds at every step;
  - the trail is about the same length at 30, 60 and 144 fps;
  - colours blend per channel as ints;
  - pixel-level draw order.
  
  Criterion 16: config.json's sha256 is unchanged after the run. Criteria 17-18 (visual): the builder's render and pixel diff are credible (changes are limited to the trail area; launcher and HUD are pixel-identical), and the UI reviewer rendered both frames on their own.
- **Tests now:** 182 passed in the worktree, and `config.json` is byte-identical before and after. Main has since gained 009-bottom-launcher and 011-collision-score-tests. A trial `merge --no-commit` of `e7952fb` onto main `383cbf3` merged without conflicts, and the merged tree passes 251/251. The scratch worktree has been removed.
- **Scope:** The diff touches only the listed files:
  - `entities/missile.py`: `IncomingMissile` only;
  - `game/constants.py`: a new block after `# Missile speeds`;
  - `systems/game_loop.py`: one 5-line loop in `draw()`, before the defense-missile loop;
  - `README.md`: one Features bullet;
  - one new test file.
  
  `DefenseMissile`, `entities/base.py`, the `LAUNCHER_*` constants and the README Gameplay paragraph are untouched. No files were deleted and no existing tests were edited.
- **Risk:** Low. The only new import is `collections.deque` from the standard library. Nothing changes the config format or how it is saved, and there is no new I/O. Memory is capped at 12 samples per missile. The game-code diff is about 55 lines, close to the 40-50 estimate. The test file is 317 lines (estimate 200-250); the extra is docstrings and stricter checks.
