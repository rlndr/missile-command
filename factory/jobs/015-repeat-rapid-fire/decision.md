APPROVE

**Reason:** Rapid-fire window now repeats every 60 s of game_time. The change is a 4-line `game_time` rule plus one constant, all 4 reviews PASS, and 377 tests pass.

## Rationale
- **Gates:** build.md says `STATUS: READY`. All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. The only finding is one UX **nit** (no warning before a window opens), which the spec puts out of scope. There are no **should** findings and the reviewers agree.
- **Criteria 1-13 (test):** each one has its own test in `tests/test_repeat_rapid_fire.py`, and I read each against the spec text: boundary lists, 2000-step on/off count, fast and normal reload, slow reload cut, short reload finishing, sound, pause, restart, frame pixels, no-audio long run, and real `config.json` untouched. The `game_time < RAPID_FIRE_START_TIME` guard is there, so `%` can't open a window at [0, 10). It uses plain `%` with `<` and adds no new attributes or wall-clock calls.
- **Criteria 14-15 (visual):** the builder and the UI reviewer each rendered frames at about 10, 125 and 135 s on their own. Both say the tower is red at 125 s and white at 135 s, with `WAVE: 5` and the reload bar unchanged. The diff adds no drawing code, so this is low risk.
- **Tests now:** I ran the suite from WT and got `377 passed in 19.42s`. The `config.json` sha1 was the same before and after the run, and the worktree is clean.
- **Scope:** 4 files changed: `README.md` (1 sentence), `game/constants.py` (1 new constant and the heading comment), `systems/game_loop.py` (only `rapid_fire_active()` body and docstring), and the new test file. There are no changes to `entities/base.py`, `systems/sound.py` or `config.json`. No existing test was edited.
- **Risk:** no new dependency, no change to the config format, no deleted files, and no core module restructured. The branch is based on current `main` (8356d30), so it merges cleanly. The new test file is about 308 lines against the spec's 150-200 estimate, which is test verbosity, not a scope issue. Game balance (17% of play time in rapid fire) is a tuning follow-up the spec already flags.
