APPROVE

**Reason:** Reload bar under the launcher meets all 16 criteria; 4/4 reviews PASS with only nits; 165 tests pass; additive, in-scope diff.

## Rationale
- **Gates:** build.md `STATUS: READY`. All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. Their only findings are nits: the test file is 272 lines against a 150-200 estimate, the dark-blue track is dim but visible, and nothing marks a blocked click. None is a should finding, and the reviewers agree.
- **Criteria:** Criteria 1-13 each have their own test in `tests/test_cooldown_indicator.py`, and I read each one against the spec. `reload_progress()` works from `cooldown_time` and `is_active`, not `cooldown_ratio`. It is clamped to [0, 1]. The fill width uses `int()`, not `round()`, and the bar geometry comes from `get_bounds()` and `self.width`. Criterion 14: I ran the suite myself and the `config.json` sha256 (`bbf68775…caa4c`) was the same before and after. Criteria 15-16 are visual: the builder and the ui reviewer each rendered the frames separately and described the same result. The 29 px fill at frame 45 (instead of 30) comes from float drift in the summed time steps, as the spec expects.
- **Tests:** I ran the README command in the worktree: `165 passed in 6.18s`. No existing test files were edited.
- **Scope:** 4 files changed: `README.md` (one sentence), `entities/base.py` (two new methods plus about 6 lines at the end of `draw_base()`, signature unchanged), `game/constants.py` (5 constants, defined after the `COLOR_*` names they use) and one new test file. `systems/game_loop.py` is untouched.
- **Risk:** Low. No new dependencies, no change to the config format or how it is saved, no deleted files, and no restructuring of core modules. The change only draws: two `pygame.draw.rect` calls per frame.
