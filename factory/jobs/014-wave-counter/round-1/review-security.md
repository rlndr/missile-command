VERDICT: PASS

## Summary
The change is pure computation and rendering. The wave is derived from `game_time` and drawn with the same per-frame font pattern the score already used. It adds no file, config or network I/O, no dangerous calls, no dependencies and no unbounded allocation. Tests are isolated from the real `config.json`.

## Findings
None.

Checked:
- `systems/game_loop.py`: `current_wave()`, `hud_wave_text()` and `draw_hud()` only read `game_time` and the score. They add no new state, no wall clock, and nothing grows per frame (two surfaces are rendered and discarded each frame, the same as the existing score HUD). `int(game_time // 30.0)` only grows linearly, and `game_time` only increases through `update()`, so there is no overflow risk a player can reach.
- No `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`__import__`/network calls in the diff. No new packages.
- `game/constants.py`: three plain literals. `README.md`: one bullet.
- `systems/score.py` / `config.json`: untouched. Nothing about waves is saved.
- `tests/test_wave_counter.py`: every test that builds a game uses the `main_game` fixture, which patches `systems.score.CONFIG_PATH` to `tmp_path` before `MainGame()` is built. The `utils.timer.time` and `handle_events` patches go through pytest's `monkeypatch`, so they are undone after each test. `test_constants` builds no game. The build notes report that a sha256 check showed `config.json` unchanged.
