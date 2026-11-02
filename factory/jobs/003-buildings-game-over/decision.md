ESCALATE

**Reason:** Clean and fully passing, but the diff is 422 changed lines (over the ~400 limit) and it changes how config.json is saved. Both are hard escalation triggers.

## Rationale
- **Reviews:** all four round-2 reviews say `VERDICT: PASS`, and build.md says `STATUS: READY`. In round 1, security asked for one **should** change (`OverflowError`/`RecursionError` not caught). It was fixed in `9f00794` with regression tests, and security confirmed the fix in round 2. The remaining findings are all nits that were deferred with reasons (atomic write, game-over delay, health-bar range, SPACE restart is backlog item 4). Reviewers don't disagree on anything.
- **Criteria:** 1–17 each map to a test in `tests/test_buildings_game_over.py`, and I read every one and they match the spec. The visual criteria 18–20 were checked by the builder and by the UI review.
- **Tests:** I re-ran the suite from the worktree and got `56 passed in 1.86s`. The `config.json` sha256 was the same before and after, and the worktree was clean afterwards. `tests/test_screen_shake.py` and `tests/test_missiles_explode.py` have no changes.
- **Scope:** the diff touches only the files listed in the spec's touch points (README, building.py, game_loop.py, score.py, the new test file). There is no new dependency, no deleted file and no new constant. A grep confirms that `check_game_over()` is now the only place that switches to `STATE_GAME_OVER` and the only caller of `save_high_score()`. The explosion-vs-building loop is fully removed.
- **Size (trigger):** +383/−39 = 422 changed lines. Game code is about 100 lines; the test file is 321 lines against the spec's estimate of about 220. The spec says outright that the last job escalated on size and asks for a compact test file.
- **config.json save (trigger):** the spec asks for this change, and the on-disk format is the same (a JSON object written with `indent=4`, other keys kept). But `save_high_score()` now behaves differently: it creates the file when it is missing, rewrites through `json.dumps` and then a truncating `open('w')`, and swallows `OSError`, `ValueError`, `TypeError`, `OverflowError` and `RecursionError`.
- **Risk:** low. The game can now actually end, and SPACE on the game-over screen rebuilds the city but doesn't resume play. That gap is known and deferred to backlog item 4.

## For the human (ESCALATE only)
1. **Size:** 422 changed lines, 321 of them in `tests/test_buildings_game_over.py`. The extra comes from the parametrised criterion 15 cases (7 file contents) and the shared helpers. Skim the test file and decide whether that size is acceptable or should be trimmed. The game code (`git -C .worktrees/003-buildings-game-over diff main...HEAD -- systems entities README.md`) is about 100 lines and reads cleanly.
2. **config.json save path:** read `systems/score.py` `save_high_score()` (about 25 lines). Confirm you're fine with these behaviours:
   - it creates `config.json` when the file is missing and the score is above 0;
   - it never touches a file it can't parse;
   - it keeps unknown keys;
   - the write is not atomic (`open('w')` truncates, then writes). The security review noted this as a nit, and making it atomic (temp file plus `os.replace`) is a possible follow-up.
3. Optional sanity check: run the game (`uv run --with pygame python main.py` or the repo's usual command). Shoot near the city and confirm buildings take no damage. Let 3 enemy hits land on one building, then let the city fall and confirm the game-over screen shows the Final Score and High Score lines.
4. Plan backlog item 4 (state flow and SPACE restart from game over) next, because a lost game can now happen in real play.
5. If all of that looks fine, run `/factory approve 003-buildings-game-over`.
