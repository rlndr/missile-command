VERDICT: PASS

## Summary
This change only touches game logic: straight-line missile flight, explosions driven by dt, and explosion-vs-missile kills. It adds no file I/O, no dangerous calls, no dependencies and no new input surface. Entity counts stay bounded, and the tests leave the real `config.json` alone.

## Findings
None.

Checked:
- **Dangerous calls / network:** the diff adds no `eval`, `exec`, `pickle`, `subprocess`, `os.system`, `__import__` or network access. `inspect` in `tests/test_missiles_explode.py` is only used to read source for the no-`get_ticks` assertion.
- **Dependencies:** no changes to `pyproject`, requirements or lock files. The tests use only pygame and pytest, as before.
- **File I/O:** `systems/score.py` is not touched. All the game-level tests use the `main_game` fixture, which redirects `CONFIG_PATH` to `tmp_path`. The pure-entity tests (`DefenseMissile`, `ExplosionPool`) don't build `MainGame` and do no I/O. I ran the full suite (33 passed). The sha256 of `config.json` was the same before and after, and `git status` was clean.
- **Input surface:** firing still goes through `spawn_defense_missile(event.pos)`. A zero-length shot no longer calls `.normalize()` on a zero vector (`entities/missile.py` `__init__`), so a click on the launcher can't raise `ValueError` and crash the game.
- **Resource exhaustion:** defense missiles are still limited by `base.can_fire()` / `start_cooldown()` (`systems/game_loop.py:108-111`). Each arrived missile makes exactly one explosion, because it is guarded by `not missile.is_destroyed` and then `destroy()`. Explosions go inactive after `EXPLOSION_EXPANSION_TIME + EXPLOSION_SHRINK_TIME` of game time, then go back to the pool through the existing filter. `DefenseMissile.update` snaps to the target and stops, so a missile can't drift off-screen and stay in the list forever (the old code had that leak). Holding or spamming the mouse can't grow any list without bound.
