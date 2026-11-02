VERDICT: PASS

## Summary
A malformed config.json now opens the game on the normal start screen showing "High Score: 0" in yellow, with no crash and no error text. I ran it headless with `{"high_score": "abc"}`. The state was `start`, the high score was 0, and the menu lines were unchanged. Controls, state flow and restart behaviour are untouched.

## Findings
None.
