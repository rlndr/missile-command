VERDICT: PASS

## Summary
Enemy trails make each missile's heading visible early, are drawn under defense missiles, enemy heads and explosions, and follow game time (dt), so pause freezes them and restart clears them. No controls changed, so there is nothing to add to the start screen or the README controls table. I judged this from the diff and the spec's own evidence, and did not run the game headless myself.

## Findings
1. **nit** `systems/game_loop.py` draw() — trails are drawn above buildings, so a diving missile can paint a few px of trail over a building in its last frames. The spec accepts this, so no change is needed.

No other findings. The constants live in `game/constants.py`, with no magic numbers in the new code. The trail is capped by a deque, stops when the missile is destroyed, and is not drawn for destroyed missiles. The trail adds no new way for the player to lose.
