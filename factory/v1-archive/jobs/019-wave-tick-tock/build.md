STATUS: READY

## Round 1
**Summary** — Added `SOUND_TICK_TOCK = (880, 660, 0.06, 0.04, 0.08)` and `"tick_tock"` in `SOUND_NAMES` in `game/constants.py`, and implemented `tick_tock()` and the `_TICK_TOCK` recipe in `systems/sound.py` using two constant-pitch `square_sweep` segments separated by a silent zero-sample gap. Wired `MainGame.update()` in `systems/game_loop.py` to compare `self.current_wave()` before and after `self.game_time += dt` (via a local `prev_wave` variable) and play `"tick_tock"` once whenever the wave increases. Updated `README.md` and added full test coverage in `tests/test_wave_tick_tock.py` (plus `SOUND_NAMES`/`DURATIONS` updates in `tests/test_sound.py` and `tests/test_rapid_fire.py`).

**Commits** — `70d6181 019-wave-tick-tock: play synthesised tick-tock sound on wave change`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants `SOUND_TICK_TOCK` and `SOUND_NAMES` | `tests/test_wave_tick_tock.py::test_constants`, `tests/test_sound.py::test_constants`, `tests/test_rapid_fire.py::test_constants` | Yes |
| 2 | `tick_tock` waveform structure and pitches | `tests/test_wave_tick_tock.py::test_tick_tock_waveform` | Yes |
| 3 | `sound_bytes` and `SoundSystem` integration | `tests/test_wave_tick_tock.py::test_sound_bytes_tick_tock_length_and_cache`, `tests/test_wave_tick_tock.py::test_sound_system_tick_tock_play_and_mute`, `tests/test_sound.py::test_sound_bytes_length_and_cache`, `tests/test_sound.py::test_sounds_built_under_dummy_driver` | Yes |
| 4 | Plays once on each wave transition during `update()` | `tests/test_wave_tick_tock.py::test_plays_once_on_each_wave_transition` | Yes |
| 5 | Start, restart, pause, and game over do not play `"tick_tock"` | `tests/test_wave_tick_tock.py::test_start_restart_pause_game_over_no_tick_tock` | Yes |
| 6 | No wave attribute added and no-audio fallback works across wave changes | `tests/test_wave_tick_tock.py::test_no_wave_attribute_added`, `tests/test_wave_tick_tock.py::test_no_audio_fallback_across_wave_change`, `tests/test_wave_counter.py::test_no_wave_bonus_or_side_effects` | Yes |
| 7 | Existing test suite and `config.json` unchanged | Full pytest suite (`444 passed`) and `tests/test_wave_tick_tock.py::real_config_untouched` | Yes |
| 8 | [visual] HUD at wave transition (`game_time == 30.0`, Wave 2) | `/tmp/wave_2_hud.png` rendered after 60 `game.update(0.5)` calls + `game.draw()`, inspected via `view_file` (`WAVE: 2` in white left of `SCORE: 30` in yellow) | Yes |

**Tests** —
```
cd /home/rory/Documents/Workspace/missile-command/.worktrees/019-wave-tick-tock && FP=/var/lib/flatpak/runtime/org.freedesktop.Platform/x86_64/25.08/a0b687431459280667d830df5c9d0f25e47b9b7d78f212a858eefac086ed2909/files && PYTHONHOME=$FP PYTHONPATH=/home/rory/.cache/uv/archive-v0/lmWZh2xTqxyONRL9/lib/python3.13/site-packages SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy $FP/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path $FP/lib/x86_64-linux-gnu $FP/bin/python3.13 -m pytest -q
```
`444 passed, 1 warning in 22.78s`
