STATUS: READY

## Round 1
**Summary** — `MainGame.rapid_fire_active()` derives the once-per-game window `[60, 70)` from `game_time`, and `update()` copies it onto the launcher with `base.set_rapid_fire(...)` straight after `game_time += dt`. `DefensiveBase` gains `rapid_fire` and `cooldown_length`; `start_cooldown()` uses the 0.1 s reload while rapid fire is on, entering the window cuts a longer running reload to 0.1 s, and `reload_progress()` / `cooldown_ratio` divide by `cooldown_length`. The tower body and barrel draw in `LAUNCHER_RAPID_FIRE_COLOR` while active and rapid; shots in the window play the new `"laser"` square-sweep sound (1800 to 300 Hz, 0.08 s) instead of `"launch"`. README gets one Gameplay sentence; `tests/test_sound.py` has only the two allowed edits (and their import).

**Commits**
- `1fc027d 013-rapid-fire-powerup: rapid-fire launcher window from 60 s to 70 s with laser sound`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_rapid_fire.py::test_constants`; `test_sound.py::test_constants` (updated SOUND_NAMES) | Yes |
| 2 | Window boundaries | `test_window_boundaries` (6 parametrised cases) | Yes |
| 3 | Launcher follows window | `test_launcher_follows_window` | Yes |
| 4 | Fast reload during window | `test_fast_reload_in_window` (1, 0, 1, then 20/20 launches) | Yes |
| 5 | Normal reload outside window | `test_normal_reload_outside_window`, `test_normal_reload_after_window`, plus `test_window_end_mid_reload_finishes_short_reload` | Yes |
| 6 | Running reload cut short on entry | `test_running_reload_cut_short`, `test_short_reload_left_alone_on_entry`, `test_switching_off_keeps_running_reload` | Yes |
| 7 | Reload bar uses current length | `test_reload_progress_uses_current_length` | Yes |
| 8 | Reset clears rapid fire | `test_init_defaults`, `test_reset_clears_rapid_fire`, `test_new_game_clears_window` | Yes |
| 9 | Pause freezes window | `test_pause_freezes_window` (600 paused frames, click while paused launches 0) | Yes |
| 10 | Laser sound on rapid shots | `test_laser_sound_on_rapid_shots` | Yes |
| 11 | Laser synthesised like others | `test_laser_bytes_length[1/2]`, `test_laser_sweep_shape`; also `test_sound.py` parametrised byte-length/duration tests now cover `"laser"` | Yes |
| 12 | Mute and no-audio | `test_laser_sound_built_and_muted`, `test_laser_no_audio_no_crash` | Yes |
| 13 | Tower colour from rendered surface | `test_tower_colour_follows_rapid_fire`; also `test_game_frame_tower_red_in_window` on a full `draw()` | Yes |
| 14 | Existing tests pass; config.json unchanged | Full suite 323 passed; only the two allowed `test_sound.py` edits; `test_real_config_untouched`; real `config.json` sha256 checked before/after the run: OK | Yes |
| 15 | [visual] Red tower in play | Rendered `main_game` frame at t=65.17 (entered via `update()`), 3 defence missiles in flight: tower body and barrel solid red, reload bar under it in its usual place (yellow, ready), HUD unchanged. Render script: `/tmp/claude-1000/-home-rory-Documents-Workspace-missile-command/cb054427-259c-4f30-b2eb-cdcfc4f6dd1e/scratchpad/013-builder/render.py`, frame `.../013-builder/t65.png` | Yes |
| 16 | [visual] Back to normal | Frame at t=70.3 (`.../013-builder/t70.png`): tower white; the tower + barrel + reload-bar region compared pixel by pixel with the t=10 frame (`.../013-builder/t10.png`): identical | Yes |

Without the change the new tests and `test_sound.py` fail at collection (missing `RAPID_FIRE_*`, `LAUNCHER_RAPID_FIRE_COLOR`, `SOUND_LASER_SWEEP` constants).

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `323 passed in 14.35s`

Notes for review:
- `set_rapid_fire()` only clamps on the off-to-on transition (`switching_on = bool(on) and not self.rapid_fire`), so calling it every frame with `True` does not re-clamp anything.
- In `spawn_defense_missile` the sound name is chosen from `self.base.rapid_fire` before `start_cooldown()`, the same flag `start_cooldown()` reads, so a laser shot always gets the 0.1 s reload.
- Criterion 5's "after the window ends" step is tested by firing a rapid shot inside the window first, then `game_time = 69.9`, `update(0.2)` twice, then a shot gets `BASE_COOLDOWN_TIME`. Read literally after the earlier 1.5 s shot at t≈10, the launcher would still be reloading.
