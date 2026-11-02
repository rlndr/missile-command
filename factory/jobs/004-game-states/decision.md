APPROVE

**Reason:** All 17 criteria met, 73 tests pass, four round-1 PASS verdicts with only nits, and the diff (398 lines) is in scope and just under the 400 cap.

## Rationale
- **Gates:** build.md says `STATUS: READY`. The code, security, ui and ux reviews for round 1 all say `VERDICT: PASS`. Every finding is a **nit**: no **should** findings and no disagreement between reviewers.
- **Tests:** I re-ran the README command in the worktree and got `73 passed in 3.46s`. The real `config.json` md5 (`3fa9655f...`) was the same before and after, and the worktree is clean. Existing tests are unchanged; the only test file touched is the new `tests/test_game_states.py`.
- **Criteria:** I read the tests against criteria 1-14 and they assert what the spec asks:
  - The parametrised no-change cases cover 4, 6, 7 and 10, including checks that the building objects are the same and in the same order.
  - Criterion 9 checks the save count stays at 1 after restart.
  - Criterion 12 drives the real loop with a controlled `utils.timer.time` and checks `game_time == 37/60`.
  - Both real-loop fakes require the script to end in quit and check the exact call count, so they can't hang.
  - Criteria 15-17 are visual. The UI reviewer and the builder both rendered those frames and confirmed them; I find that credible.
- **Code:**
  - `handle_actions()` picks the transition from the state at the start of the call. It makes at most one change, calls `timer.reset()` on start, resume and restart, and fires only when the game was playing both before and after.
  - `self.state = STATE_PLAYING` now appears only in `handle_actions()`.
  - The `"pause"`, `"start_pause"` and `"resume"` strings are gone.
  - The branch that removed buildings while iterating over the list is deleted, not just made unreachable.
  - `get_ticks` is left only in the dead `handle_score_updates()`, as the spec allows.
- **Scope and risk:**
  - Four files changed: `README.md`, `systems/game_loop.py`, `systems/input_system.py` and the new test file.
  - No new dependency and no change to `config.json`'s format or how it is saved. `save_high_score()` is still called only from `check_game_over()`.
  - `entities/base.py` is untouched. The `game_loop.py` changes are the ones the spec asked for.
  - Size is 308 insertions and 90 deletions, 398 in total. That is under the spec's hard limit of 400. Game code is about 90 lines, as expected; the tests are 231 lines, a little over the ~200 target.
- **Follow-ups for the backlog (not blockers):**
  - `load_high_score()` crashes on a malformed `config.json` (security nit).
  - The launcher cooldown is not reset on restart (ux nit, out of scope).
  - The pause screen lists "SPACE: Start / Restart", but SPACE does nothing while paused (ux nit; the spec requires that line).
