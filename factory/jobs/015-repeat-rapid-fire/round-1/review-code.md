VERDICT: PASS

## Summary
The change matches the spec. `rapid_fire_active()` keeps the `< START_TIME` guard and uses plain `%` with `<`, and it works from `game_time` only. The constant, README sentence and new tests are in place, and `entities/base.py` and `systems/sound.py` are untouched. The full suite gave 377 passed.

## Findings
None.
