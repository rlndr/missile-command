VERDICT: PASS

## Summary
The wave counter is a passive HUD item derived from `game_time`. It freezes on pause and menus and resets on restart, and it adds no new controls or penalties. It stays in the existing top-right HUD row beside the score.

## Findings
1. **nit** `systems/game_loop.py:236` — The change from wave N to N+1 is silent, and the HUD number is the only cue. The spec accepts this. A later job could add a short flash or sound, and could tie spawn rate to the wave so the counter means something.
2. **nit** `systems/game_loop.py:240` — The wave is white at 36 pt over the light top of the sky. The builder's frame check says it is legible. I did not re-render it.
