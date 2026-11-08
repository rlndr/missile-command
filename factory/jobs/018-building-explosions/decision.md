APPROVE

**Reason:** Nearest-point `building_in_explosion` check and fiery building destruction explosions match the spec cleanly, all 433 tests pass, and all four reviewers passed with no findings.

## Rationale
- **Criteria:** All 12 acceptance criteria (10 automated test criteria in `tests/test_building_explosions.py` and 2 visual criteria verified on rendered frames) are met with clear evidence.
- **Tests:** Full test suite passes (`433 passed` in `22.01s`), with existing test files untouched.
- **Scope:** Changes are strictly limited to the specified touch points (`systems/collision.py`, `game/constants.py`, `entities/terrain.py`, `systems/game_loop.py`, `README.md`, and `tests/test_building_explosions.py`).
- **Risk:** Low; pooled explosion instances reset `is_building` and timing fields on reuse, fire flicker is a pure function of `elapsed` so paused frames stay deterministic, and no dependencies, config formats, or file I/O paths were changed.
