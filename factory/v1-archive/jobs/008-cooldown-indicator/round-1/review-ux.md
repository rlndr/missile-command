VERDICT: PASS

## Summary
The reload bar gives immediate feedback on firing (empty on shot, orange fill, yellow when ready) and is only yellow when `can_fire()` is true. It freezes on pause and resets to full on restart. Controls are unchanged and the README explains the bar.

## Findings
1. **nit** `entities/base.py:~113` — Nothing marks a blocked click, but the bar already shows the reload state, which is what the spec asked for. No change needed.
