VERDICT: PASS

## Summary
The diff matches the spec: the wave is derived from `game_time`, with no new attribute or timer, and `update()`, `start_game()` and the 013 areas are untouched. Tests: `308 passed in 14.44s`.

## Findings
1. **nit** `tests/test_wave_counter.py:112-113` — The second `vars(game)` assertion repeats the first one in a weaker form. It is harmless, so drop it if you touch the file again.
