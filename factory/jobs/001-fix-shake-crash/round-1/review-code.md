VERDICT: PASS

## Summary
The fix ceils the amplitude before `randint`, constants are extracted, and the harness isolates config. Suite: `10 passed in 0.61s`; worktree clean (config.json unmodified).

## Findings
1. **nit** `tests/conftest.py:46` — `del game` in the fixture only drops the local name; harmless since gc.collect and pytest drop the reference. No action needed.
