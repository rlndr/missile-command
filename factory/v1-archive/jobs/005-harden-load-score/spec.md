# 005-harden-load-score: Fall back to a high score of 0 when config.json is malformed

## Problem
`ScoreSystem.load_high_score()` runs inside `ScoreSystem.__init__`, which `MainGame.__init__`
calls, so it runs on every launch. It only catches `FileNotFoundError` and
`json.JSONDecodeError`, so a bad but readable `config.json` crashes the game before the start
screen shows:
- `{"high_score": "abc"}` raises `ValueError` from `int()`.
- A top-level `[]` raises `AttributeError` because a list has no `.get`.
- `1e999` parses to `inf`, so `int()` raises `OverflowError`.
- An integer with more than 4300 digits makes `json.load` itself raise a plain `ValueError`
  (Python 3.11+ integer string limit).

`save_high_score()` was hardened in job 003 and never raises on these files. Loading should be
just as safe and give a high score of 0.

## Scope
- **`ScoreSystem.load_high_score()` never raises.** It returns an `int` in
  `0..HIGH_SCORE_MAX`, read like this:
  - Missing file → 0 (unchanged).
  - The file parses to something that is not a JSON object (list, string, number, `null`)
    → 0.
  - It is an object with no `"high_score"` key → 0 (unchanged).
  - Otherwise convert the value with `int(...)`, the same conversion `save_high_score()` uses.
    So `250` → 250 and `"120"` → 120.
  - If the conversion fails, or the result is below 0 or above `HIGH_SCORE_MAX`, return 0.
  - If reading or parsing fails, return 0. That covers at least `OSError` (directory,
    permission), `ValueError` (which includes `JSONDecodeError`, `UnicodeDecodeError` and the
    4300-digit limit), `TypeError`, `OverflowError` and `RecursionError`. This is the same set
    `save_high_score()` catches. Use an `isinstance(config, dict)` check, not
    `except AttributeError`.
  - Loading is read-only. It never writes, creates or truncates `CONFIG_PATH`.
- **New constant `HIGH_SCORE_MAX = 999_999_999`** in `game/constants.py`. It is the largest
  stored high score that is believed. Anything larger, such as a 4000-digit integer that fits
  under Python's limit, loads as 0. This keeps a hand-edited or hostile number out of the
  `f"High Score: {...:,}"` text on the start and game-over screens.
- Replace the `load_high_score()` docstring with one in the style of `save_high_score()`'s.
  It should state the fallback rule and that the method never raises.
- **Tests.** New file `tests/test_load_high_score.py`.

## Out of scope
- Any change to how `save_high_score()` behaves. Today a stored value above `HIGH_SCORE_MAX`
  makes save leave the file alone (`score <= int(stored)`), and that stays. Sharing one
  parse/validate helper between load and save is a later refactor.
- Rewriting or repairing a malformed `config.json`, logging or showing a warning about it, and
  backing up the bad file.
- Reading the other `config.json` keys (`sound_enabled`, `difficulty_multiplier`, ...).
- Limiting the file size. A multi-megabyte `config.json` is still read fully into memory.
- Reloading the high score on restart. It is still read once, in `ScoreSystem.__init__`.
- Scoring (next backlog item). Real play still scores about 0.

## Acceptance criteria
Every test monkeypatches `systems.score.CONFIG_PATH` to `tmp_path / "config.json"` **before**
it constructs a `ScoreSystem` or `MainGame`, then writes the file contents (text, or raw bytes
for the non-UTF-8 case in criterion 4). "Loads as N" means `ScoreSystem().high_score == N`,
construction raises nothing, `type(high_score) is int`, and the file's bytes are the same
before and after.

1. [test] **The four cases from the feature load as 0:**
   - `{"high_score": "abc"}`
   - `[]`
   - `1e999` (top level)
   - `'{"high_score": ' + "1" * 4301 + '}'`
2. [test] **Other non-numbers load as 0:**
   - `{"high_score": 1e999}`
   - `{"high_score": Infinity}`
   - `{"high_score": -Infinity}`
   - `{"high_score": NaN}`
   - `{"high_score": null}`
   - `{"high_score": [1]}`
   - `{"high_score": {}}`
3. [test] **Other non-objects load as 0:** `"abc"` (a JSON string), `42` (a top-level number),
   `null`, `[1, 2]`.
4. [test] **Unparseable files load as 0:**
   - `{not json`
   - an empty file `""`
   - `"[" * 200_000` (deep nesting)
   - the raw bytes `b"\xff\xfe\x00{"` (not UTF-8)
5. [test] **Out-of-range values load as 0:**
   - `{"high_score": -5}`
   - `{"high_score": HIGH_SCORE_MAX + 1}`
   - `json.dumps({"high_score": 10**4000})` (4001 digits, under the parse limit)
   - `json.dumps({"high_score": "1" * 4000})`
6. [test] **Good files still load:**
   - `{"high_score": 250}` → 250
   - `{"high_score": 0}` → 0
   - `{"high_score": HIGH_SCORE_MAX}` → `HIGH_SCORE_MAX`
   - `{"high_score": "120"}` → 120
   - `{}` → 0
   - the real config's keys (`REAL_CONFIG_KEYS` from `tests/test_buildings_game_over.py`, with
     `high_score: 50`) → 50
7. [test] **Missing file:** with no file at `CONFIG_PATH`, `ScoreSystem().high_score == 0` and
   no file is created.
8. [test] **Unreadable path:** with `CONFIG_PATH` a directory (`path.mkdir()`),
   `ScoreSystem()` raises nothing and `high_score == 0`.
9. [test] **The game launches with a bad file:** for each of the four files in criterion 1:
   - `MainGame()` constructs without raising;
   - `game.state == STATE_START` and `game.score_system.high_score == 0`;
   - `game.menu_lines()` has a line whose text is exactly `"High Score: 0"` with colour
     `COLOR_YELLOW`;
   - `game.draw_start_screen()` raises nothing.

   Clean up as the `fresh_game` fixture in `tests/test_game_states.py` does: `gc.collect()`
   before, and `gc.collect()` + `pygame.quit()` after.
10. [test] **The real loop runs:** with the `[]` file, monkeypatch `game.handle_events` so its
    first call returns `{"quit": True}`. `game.start_game_loop()` returns normally.
11. [test] **A bad file isn't overwritten after the fallback:**
    - The file is `{"high_score": "abc", "sound_enabled": false}`.
    - Construct a `ScoreSystem` (it loads 0), set `score = 120` and call `save_high_score()`.
    - The file bytes are unchanged and `high_score == 120`.
    - Repeat with `[]`. Same result.
12. [test] **Loading is read-only:** take one good file (criterion 6, 250) and one bad file
    (criterion 1, `[]`). For each, call `load_high_score()` 3 more times on the same
    `ScoreSystem`. Every call returns the same value, and the file bytes and
    `os.path.getmtime` don't change.
13. [test] **No regressions:** the existing tests in `tests/` pass unchanged, and the full suite
    passes with the README command. The real `REPO/config.json` is byte-for-byte unchanged
    after the run (`git status` clean for it).
14. [visual] **Start screen after a bad file:**
    - Write `{"high_score": "abc"}`, construct `MainGame()`, call `draw_start_screen()` and save
      the frame with `pygame.image.save`.
    - It looks like the normal start screen: "Missile Command Clone" in `COLOR_WHITE`,
      "Defend the city!" in `COLOR_GRAY`, then "High Score: 0" in `COLOR_YELLOW`, then the
      controls and "Press SPACE to Start".
    - There is no error text and nothing is cut off.

## Touch points
- `systems/score.py`: `ScoreSystem.load_high_score()` (body and docstring). Nothing else in
  the file should change.
- `game/constants.py`: new section `# High score` with
  `HIGH_SCORE_MAX = 999_999_999  # Largest stored high score that is believed`. `score.py`
  already does `from game.constants import *`.
- `tests/test_load_high_score.py` (new). Use `pytest.mark.parametrize` over the file contents,
  plus one small helper that writes the file, builds `ScoreSystem()` and checks the bytes
  didn't change.
- `tests/test_buildings_game_over.py`: optional. The `_score_system` docstring says
  `load_high_score()` "is not hardened yet". That sentence may be updated, but leave the test
  logic alone.

Expected diff: about 20 lines of game code and about 120 lines of tests.

## Notes for reviewers
- **security:** this is the hostile-file path at launch.
  - Check that every case in criteria 1–5 and 8 gives 0 without raising. In particular, the
    4300-digit `ValueError` comes from `json.load`, not from `int()`, so the `try` must wrap
    the parse as well as the conversion.
  - Check that `HIGH_SCORE_MAX` is applied after `int()`, so a huge digit *string* is rejected
    too.
  - Load must never open the file for writing.
  - The catch list should be explicit (no bare `except:` and no `except Exception`). The one
    exception: if the builder can show a case the listed types miss, it can be added with a
    comment.
  - Tests must never touch the real `config.json`: `CONFIG_PATH` is patched before any
    construction. No new dependencies.
- **code:**
  - Prefer the `isinstance(config, dict)` check to catching `AttributeError`.
  - Keep the conversion rule identical to `save_high_score()`'s (`int(value)`), so the two
    methods agree on which files are readable, apart from the new range check.
  - The method must return the result of `int(...)` (or the literal `0`), never the raw value
    from the dict. That keeps `type(high_score) is int` true; for example, `true` in the file
    becomes `1`, not `True`.
  - Check that the 200 000-deep nesting test doesn't leave the interpreter in a bad state for
    later tests. It already passes for `save_high_score()`.
- **ux:** the only player-facing change: a corrupted or hand-edited `config.json` no longer
  stops the game from opening. The player sees "High Score: 0" instead of a crash. The bad
  file stays as it is (criterion 11). A player who edits the file to an absurd value also
  sees 0, which is intended.
- **ui:** no layout change. Confirm that the criterion 14 frame matches the normal start
  screen and "High Score: 0" is centred in `COLOR_YELLOW`.
