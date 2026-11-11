VERDICT: PASS

## Summary
This is a rendering-only change. The pause branch now draws the scene, then a dim overlay, then the text, and `menu_lines()` gets a separate pause list. It adds no file, config, network or subprocess I/O, no dangerous calls and no new dependencies. The tests keep away from the real `config.json`, and every monkeypatch is scoped to its test.

## Findings
None.

Checked:
- `systems/game_loop.py`: no `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`__import__`/network. Imports are unchanged; `PAUSE_OVERLAY_*` arrive through the existing `from game.constants import *`. `systems/score.py` is untouched, so config read/write behaviour is the same.
- Resource use: the pause overlay `SRCALPHA` surface is built once in `__init__` and reused. Pausing does not allocate a new surface each frame and adds no entities. `draw_scene()` only reads state; it does not grow trails, lists or pools while paused (criterion 7 covers this). The start and game over screens still build a new overlay surface every frame, but that code existed before and this job did not change it.
- Tests (`tests/test_pause_overlay.py`): all use the `main_game` fixture, which points `systems.score.CONFIG_PATH` at `tmp_path`. The `pygame.display.flip`, `utils.timer.time`, `handle_events`, `draw_scene` and `draw_start_screen` patches all go through `monkeypatch`, so they are undone after each test. The event queue is cleared before and after each posted key event. The real-loop test ends on a scripted `{"quit": True}`, so it cannot hang. The builder reports the `config.json` md5 was the same before and after the suite.
- README and constants: text and two constant values only.
