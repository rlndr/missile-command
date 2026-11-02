ESCALATE

**Reason:** Clean, all-PASS build, but the diff is 589 lines (over the ~400 limit) and criterion 12's frame-80 bound was relaxed to 82 because it contradicts criterion 6.

## Rationale
- **Reviews:** all four round-1 reviews say `VERDICT: PASS` and build.md says `STATUS: READY`. Reviewers flagged only nits, and none disagree.
- **Tests:** I re-ran the suite from the worktree and got `33 passed in 1.05s`. The sha256 of `config.json` was the same before and after, and `git status` was clean.
- **Criteria:** 1-11 and 13-19 are met with credible evidence. I read the code and tests myself:
  - Arrival snaps to the target when the remaining distance is `<= speed*dt`.
  - A zero-length shot gets zero velocity and never calls `.normalize()`.
  - Explosion activity depends on `elapsed`.
  - The pool resets `position`, `is_player`, `radius`, `elapsed` and `is_active`.
  - The kill check uses the current radius and only runs for player explosions.
  - The duplicate `Explosion` was removed from `entities/base.py`.
  - The UI reviewer checked both visual frames.
- **Criterion 12 is not met as written.** The spec says the kill lands "on or before frame 80". The test asserts `75 <= killed_on <= 82`, and the actual kill is on frame 82. The builder's arithmetic is correct: the explosion grows from radius 0 by about 2.67 px per frame after arrival on frame 75, so it reaches a missile 20 px away on frame 82. Criteria 6 and 12 contradict each other. The builder documented the deviation instead of hiding it.
- **Scope and size:** every touched file is listed in the spec. No dependencies were added, `config.json` and its save path are untouched, and no files were deleted. The `entities/base.py` change is only the deletion of the duplicate `Explosion` class, which the spec asked for. `systems/game_loop.py` has only the two edits the spec asked for. The total is still 432 insertions and 157 deletions (589 changed lines), over the ~400 trigger. The spec expected about 365 lines. Game code alone is 80+/149-. The overage is mostly the 340-line test file.
- **Risk:** low. The game-code change is small and well tested. Escalating is due to the size trigger and the criterion-12 deviation, not to a defect.

## For the human (ESCALATE only)
1. **Criterion 12 bound:** decide whether a kill on frame 82 (about 0.12 s later than the spec's frame 80) is acceptable. If it is, accept the relaxed assertion in `tests/test_missiles_explode.py::test_end_to_end_intercept`. If not, send it back with a choice: a shorter `EXPLOSION_EXPANSION_TIME`, a non-zero starting radius (this would break criterion 6 as written), or a looser criterion.
2. **Diff size:** check that the extra lines are tests and not game code. `git -C .worktrees/002-missiles-explode diff --stat main...HEAD` should show `tests/test_missiles_explode.py` at about 340 lines and game code at about 80+/149-.
3. **Optional playtest:** run the game, click about 2 s after start (the first 1.5 s are blocked by cooldown), and confirm the straight flight and that the growing explosion doesn't feel sluggish. Known deferred gaps: a player explosion near a building's top-left corner still damages it (backlog item 3), and kills score nothing (backlog item 5).
4. If all of that is fine: `/factory approve 002-missiles-explode`.
