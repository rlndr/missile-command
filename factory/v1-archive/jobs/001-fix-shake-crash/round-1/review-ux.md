VERDICT: PASS

## Summary
The fix removes a crash on the frame after any building hit or intercept. No controls, timings or state flow changed, so no README controls update is needed. Shake is still invisible, as the spec intends.

## Findings
1. **nit** `systems/game_loop.py:51` — `start_game()` doesn't reset `shake_intensity`, so a restart within about 2.5 s of a hit carries leftover shake. It is pre-existing, has no visual effect now, and decays on its own. Consider resetting it in `start_game()` when shake is rendered in a later job.
