APPROVE

**Reason:** Shake offset is now ceiled to int before randint, all 10 criteria are met, 10/10 tests pass, the change stays in scope, and all four reviews passed with only nits.

## Rationale
- **Gates:** build.md says `STATUS: READY`. All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. The only findings are nits, and they are pre-existing or have no effect: the `del game` local in the fixture, `score.py` exception handling, and `start_game()` not resetting shake. There are no unresolved **should** findings and the reviewers agree.
- **Criteria:** Each of criteria 1-9 maps to a named test in `tests/test_screen_shake.py`, and I read each one against the spec wording. Criterion 10 (visual) was checked by the builder, including a pixel-identical comparison of the hit frame against `main`, and confirmed by the UI reviewer. The draw code is unchanged apart from the offset call.
- **Regression proof:** I ran the new tests against `main`'s `game_loop.py` myself (constant name swapped in so the import works). They fail with `TypeError: 'float' object cannot be interpreted as an integer` from `random.randint`, so the tests do exercise the bug.
- **Tests now:** `10 passed` with the SDL dummy env vars, and again with them unset (conftest sets them). The `config.json` sha256 is the same before and after, and the worktree is clean.
- **Scope:** 5 files, +232/-5, close to the expected ~20 lines of game code plus ~150 of tests. There are no new runtime dependencies (pytest is dev-only and documented in the README), no change to the config format or how it is saved, and no files deleted. The `systems/game_loop.py` change is limited to the spec's touch points: `import math`, `get_shake_offset()`, and the constants swapped in. `entities/base.py` is untouched.
- **Risk:** Low. Constant values are unchanged, so the decay behaviour is the same. The fixture patches `CONFIG_PATH` before `MainGame()` is built, and no test reaches `save_high_score()`. `gc.collect()` runs at setup and teardown, so a stale `MainGame.__del__` can't call `pygame.quit()` partway through a later test.
