# 019-wave-tick-tock: Play a synthesised tick-tock sound when the wave changes

## Problem
The HUD wave counter increases by 1 every `WAVE_DURATION` (`30.0`) seconds of play (`014-wave-counter`),
but the transition from wave `N` to wave `N + 1` is completely silent. When the player's eyes are on
incoming missiles in the sky, nothing alerts them that a new wave has started. We want a retro,
procedurally synthesised two-tone "tick-tock" sound effect played once whenever the wave number
increases during play.

## Scope
- **Constants** (`game/constants.py`), in the `# Sound` section:
  - `SOUND_TICK_TOCK = (880, 660, 0.06, 0.04, 0.08)`: `(tick_hz, tock_hz, tick_duration, gap_duration, tock_duration)` — a higher-pitched `880` Hz square-wave "tick" (`0.06` s), a silent gap (`0.04` s), and a lower-pitched `660` Hz square-wave "tock" (`0.08` s), for a total duration of `0.18` s.
  - Append `"tick_tock"` to `SOUND_NAMES`:
    `SOUND_NAMES = ("launch", "explosion", "intercept", "impact", "game_over", "laser", "tick_tock")`.
- **Synthesis** (`systems/sound.py`):
  - New function `tick_tock(tick_hz, tock_hz, tick_duration, gap_duration, tock_duration, sample_rate=SOUND_SAMPLE_RATE, volume=SOUND_VOLUME)` returning an `array.array('h')` of mono signed 16-bit samples:
    - Builds the "tick" segment with `square_sweep(tick_hz, tick_hz, tick_duration, sample_rate, volume)` (`round(tick_duration * sample_rate)` samples at constant `tick_hz`, peak `round(volume * 32767)`, fading linearly to `0` over the last `SOUND_FADE_TIME` seconds).
    - Builds the middle silence gap of `round(gap_duration * sample_rate)` zero samples (`0`).
    - Builds the "tock" segment with `square_sweep(tock_hz, tock_hz, tock_duration, sample_rate, volume)` (`round(tock_duration * sample_rate)` samples at constant `tock_hz`, peak `round(volume * 32767)`, fading linearly to `0` over the last `SOUND_FADE_TIME` seconds).
    - Returns the concatenated `array('h')` `tick + gap + tock` of total length `round(tick_duration * sample_rate) + round(gap_duration * sample_rate) + round(tock_duration * sample_rate)`.
  - Add recipe kind `_TICK_TOCK = "tick_tock"` and entry `"tick_tock": (_TICK_TOCK, SOUND_TICK_TOCK)` to `_RECIPES`, and dispatch `_TICK_TOCK` in `sound_bytes(name, sample_rate, channels)` to `tick_tock(*args, sample_rate)` before interleaving channels.
  - Because `"tick_tock"` is in `SOUND_NAMES` and goes through `SoundSystem`, it is cached by `sound_bytes`, built when the mixer is available, silenced when `muted` is `True` (`M` key), and no-ops when `available` is `False`.
- **Wave-change trigger** (`systems/game_loop.py`, `MainGame.update`):
  - At the start of `MainGame.update(self, dt)`, capture `prev_wave = self.current_wave()` as a local variable before `self.game_time += dt`.
  - Immediately after `self.game_time += dt`, if `self.current_wave() > prev_wave`, call `self.sound.play("tick_tock")` once.
  - Do not add any wave attribute (`self.wave`, `self.last_wave`, etc.) to `MainGame`; `current_wave()` remains derived solely from `self.game_time`, and `vars(game)` gains no key containing `"wave"`.
  - Starting or restarting a game (`start_game()`, entering Wave 1 at `game_time = 0.0`) does not play `"tick_tock"`.
- **README** (`README.md`):
  - Update the wave-counter bullet in `## Features` to mention the tick-tock sound on each wave change.
  - Mention wave changes alongside the other retro-style synthesised sound effects in `## Gameplay`.
- **Tests**:
  - New file `tests/test_wave_tick_tock.py`.
  - In `tests/test_sound.py`, add `"tick_tock"` to the `SOUND_NAMES` tuple in `test_constants`, add `"tick_tock": sum(SOUND_TICK_TOCK[2:])` to `DURATIONS`, and import `SOUND_TICK_TOCK`.
  - In `tests/test_rapid_fire.py`, add `"tick_tock"` to the `SOUND_NAMES` tuple in `test_constants`.
  - Do not edit `tests/test_wave_counter.py` or any other existing test file.

## Out of scope
- Visual wave-change banners, HUD flashes, or text animations when the wave advances.
- Continuous per-second countdown ticks before a wave ends.
- Changing `WAVE_DURATION` (`30.0` s) or tying enemy spawn rates or scoring bonuses to the wave number.
- Persisting sound or wave state to `config.json`, or adding audio asset files.

## Acceptance criteria
Terms used below:
- `SR = 22050` and `PEAK = round(SOUND_VOLUME * 32767)`.
- `n(d, sr) = round(d * sr)`.
- **Sign changes** means the number of sign flips between consecutive non-zero samples.
- A **spy** on `main_game` is `calls = []` plus `monkeypatch.setattr(game.sound, "play", lambda name: calls.append(name) or True)`.

1. [test] **Constants.**
   - `SOUND_TICK_TOCK == (880, 660, 0.06, 0.04, 0.08)`.
   - `SOUND_NAMES == ("launch", "explosion", "intercept", "impact", "game_over", "laser", "tick_tock")`.
2. [test] **`tick_tock` waveform structure and pitches.**
   For `s = tick_tock(*SOUND_TICK_TOCK, SR)` with `n_tick = n(0.06, SR) == 1323`, `n_gap = n(0.04, SR) == 882`, and `n_tock = n(0.08, SR) == 1764`:
   - `s.typecode == 'h'` and `len(s) == n_tick + n_gap + n_tock == 3969 == n(0.18, SR)`.
   - `tick = s[:n_tick]`: `abs(tick[0]) == PEAK`, `max(abs(x) for x in tick) <= PEAK`, and `tick[-1] == 0`.
   - `gap = s[n_tick:n_tick + n_gap]`: `len(gap) == n_gap` and `all(x == 0 for x in gap)`.
   - `tock = s[n_tick + n_gap:]`: `abs(tock[0]) == PEAK`, `max(abs(x) for x in tock) <= PEAK`, and `tock[-1] == 0`.
   - Both `tick` and `tock` have between 100 and 110 sign changes, and the higher-pitched `tick` has a strictly higher sign-change rate per sample than `tock`: `(sign_changes(tick) / len(tick)) > 1.25 * (sign_changes(tock) / len(tock))`.
3. [test] **`sound_bytes` and `SoundSystem` integration.**
   - For `channels` in `(1, 2)`, `len(sound_bytes("tick_tock", SR, channels)) == n(0.18, SR) * 2 * channels`, and a second call with the same arguments returns the cached `bytes` object (`is`).
   - Under the dummy audio driver (`main_game`), `"tick_tock" in game.sound.sounds`, `game.sound.sounds["tick_tock"].get_length() == pytest.approx(0.18, abs=0.02)`, `game.sound.play("tick_tock") is True`, and after `game.sound.toggle_mute()`, `game.sound.play("tick_tock") is False` (skip only if `pygame.mixer` is missing from the pygame build).
4. [test] **Plays once on each wave transition during `update()`.**
   On `main_game` with a spy:
   - Starting from `game_time == 0.0`, 59 calls to `game.update(0.5)` (`game_time == 29.5`, still Wave 1) produce zero `"tick_tock"` calls (`calls.count("tick_tock") == 0`).
   - The 60th `game.update(0.5)` (`game_time == 30.0`, Wave 1 → Wave 2) plays `"tick_tock"` once (`calls.count("tick_tock") == 1`).
   - Calling `game.update(0.5)` 59 more times (`game_time == 59.5`, still Wave 2) adds no `"tick_tock"` (`calls.count("tick_tock") == 1`).
   - The next `game.update(0.5)` (`game_time == 60.0`, Wave 2 → Wave 3) plays `"tick_tock"` a second time (`calls.count("tick_tock") == 2`).
   - Advancing through `game_time == 90.0` (Wave 4) and `120.0` (Wave 5) plays `"tick_tock"` once at each boundary (`calls.count("tick_tock") == 4`).
5. [test] **Start, restart, pause, and game over do not play `"tick_tock"`.**
   On `main_game` with a spy:
   - `game.start_game()` adds no `"tick_tock"` to `calls`.
   - With `game.game_time = 29.9`, pausing via `game.handle_actions({"toggle_pause": True})`, running 100 `game.handle_actions({})` + `game.draw_start_screen()` frames, and resuming via `game.handle_actions({"toggle_pause": True})` adds no `"tick_tock"`; one subsequent `game.update(0.2)` in `STATE_PLAYING` (`game_time == 30.1`, Wave 2) adds `"tick_tock"` once.
   - Destroying all buildings, calling `game.check_collisions()` and `game.check_game_over()` (`STATE_GAME_OVER`), and restarting with `game.handle_actions({"start": True})` adds `"game_over"` on game over and no `"tick_tock"`.
6. [test] **No wave attribute added and no-audio fallback works across wave changes.**
   - After crossing from Wave 1 to Wave 2 via `game.update()`, `[k for k in vars(game) if "wave" in k.lower()] == []`.
   - With `pygame.mixer.get_init` patched to `lambda: None` and `pygame.mixer.init` raising `pygame.error("no audio")`, a fresh `MainGame()` has `game.sound.available is False`, and advancing across `game_time = 30.0` (`game.game_time = 29.5; game.update(1.0)`) reaches Wave 2 without raising.
7. [test] **Existing test suite and `config.json`.**
   All existing tests pass (including `tests/test_wave_counter.py` unedited, plus `tests/test_sound.py` and `tests/test_rapid_fire.py` with `"tick_tock"` in `SOUND_NAMES`), and the real `config.json` is byte-for-byte unchanged.
8. [visual] **HUD at wave transition.**
   On `main_game`, advance `game.update(0.5)` 60 times to `game_time == 30.0` (Wave 2, when `"tick_tock"` plays) and call `game.draw()`. The top-right HUD cleanly displays `WAVE: 2` in white (`HUD_WAVE_COLOR`) to the left of `SCORE: 30` in yellow (`COLOR_YELLOW`), with the battlefield and launcher unchanged.

## Touch points
- `game/constants.py`: add `SOUND_TICK_TOCK = (880, 660, 0.06, 0.04, 0.08)` and append `"tick_tock"` to `SOUND_NAMES` in `# Sound`.
- `systems/sound.py`: add `_TICK_TOCK = "tick_tock"`, `"tick_tock": (_TICK_TOCK, SOUND_TICK_TOCK)` in `_RECIPES`, new `tick_tock(...)` function, and `_TICK_TOCK` branch in `sound_bytes()`.
- `systems/game_loop.py`: `MainGame.update(self, dt)` (compare `self.current_wave()` before and after `self.game_time += dt` and call `self.sound.play("tick_tock")` when it increases).
- `README.md`: update the wave-counter bullet in `## Features` and the sound sentence in `## Gameplay`.
- `tests/test_wave_tick_tock.py` (new), plus the `SOUND_NAMES` / `DURATIONS` updates in `tests/test_sound.py` and `tests/test_rapid_fire.py`.

## Notes for reviewers
- **code:**
  - `tick_tock` must reuse `square_sweep` (or pure deterministic square-wave phase accumulation) and zero bytes for the gap, with no `random` module, numpy, or external audio files (`tests/test_sound.py::test_no_global_randomness` and `test_sound_module_does_not_import_random` check all names in `SOUND_NAMES`).
  - At `22050` Hz, `0.06 * 22050 == 1323`, `0.04 * 22050 == 882`, `0.08 * 22050 == 1764`, and `0.18 * 22050 == 3969 == 1323 + 882 + 1764`, so `len(sound_bytes("tick_tock", 22050, channels))` matches `round(sum(SOUND_TICK_TOCK[2:]) * 22050) * 2 * channels` with no rounding mismatch in `tests/test_sound.py::test_sound_bytes_length_and_cache`.
  - Keep `prev_wave` as a local variable in `MainGame.update()` rather than an attribute on `self`. `tests/test_wave_counter.py::test_no_wave_bonus_or_side_effects` explicitly asserts `not [k for k in vars(game) if "wave" in k.lower()]`.
- **security:** No file, network, or config I/O is added. Tests must keep `systems.score.CONFIG_PATH` isolated via `main_game` or `monkeypatch`.
- **ux / ui:**
  - The 880 Hz → 660 Hz two-step pattern (a musical fourth down with a 40 ms gap) is distinct from the rising launch/intercept sweeps, falling laser/game-over sweeps, and noise bursts used for explosions/impacts.
  - Because each `square_sweep` segment fades to `0` over its final `SOUND_FADE_TIME` (`0.01` s), neither the end of the "tick" nor the end of the "tock" pops or clicks.
