VERDICT: PASS

## Summary
`load_high_score()` wraps parse and conversion in one explicit try, uses an isinstance(dict) check, applies HIGH_SCORE_MAX after int(), and only opens the file read-only. Full suite run myself: 113 passed.

## Findings
None.
