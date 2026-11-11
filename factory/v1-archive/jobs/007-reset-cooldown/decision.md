APPROVE

**Reason:** Launcher reset in place from start_game(). All 12 criteria are met, 4/4 reviews PASS, 147 tests pass, and the diff stays in scope.

## Rationale
- **Gates:** All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. build.md says `STATUS: READY`. Only two nits were raised, both in review-code, and there are no **should** findings. The reviewers agree.
- **Criteria 1-10:** Each has its own test in `tests/test_reset_cooldown.py`. Criterion 3 is parametrised (2 states x 3 leftovers). build.md says 14 of the 15 new tests fail without the fix. The one that passes is the criterion 4 guard test, which is expected.
- **Criterion 6 deviation:** The spec asked for `len(defense_missiles)`. The test counts launches through a recording `DefenseMissile` subclass instead. The reason is sound: the first missile reaches its target at about 1.24 s, before frame 89, so the live list would hold 0. The test still checks the spec's intent (no shot before 1.5 s, one shot after it). build.md documents the change and review-code accepted it as a nit.
- **Criterion 11:** I re-ran the suite myself and got `147 passed`. The `config.json` sha256 was `bbf68775…caa4c` before and after, and the worktree is clean.
- **Criterion 12:** The UI reviewer and build.md both checked the rendered frame: a yellow missile about 63 px along the path, and the HUD reads `SCORE: 0`.
- **Scope:** Three files changed. `entities/base.py` gets the new 3-line `reset()` method. `systems/game_loop.py` gets one `self.base.reset()` call in `start_game()` and loses the dead `base_cooldown` line. `tests/test_reset_cooldown.py` is new. No existing test files were edited and `DefensiveBase.__init__` is unchanged. The pause and resume branches don't touch the base.
- **Risk:** Low. There are no new dependencies, no change to the config format or how it's saved, no deleted files, and no restructuring of core modules. All test patches go through `monkeypatch`, and `CONFIG_PATH` is patched before any `MainGame` is built.
