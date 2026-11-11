APPROVE

**Reason:** Synthesised `tick_tock` wave-transition sound effect meets all 8 acceptance criteria with 444 passing tests and unanimous PASS verdicts across all four reviewers.

## Rationale
- **Criteria:** All 8 acceptance criteria (constants, `tick_tock` waveform synthesis & pitch ratios, `sound_bytes`/`SoundSystem` caching & mute behavior, single trigger per wave boundary in `MainGame.update()`, silence on start/pause/game-over/restart, no wave attributes added & no-audio fallback, existing suite & `config.json` preservation, and HUD visual state at Wave 2) are verified.
- **Tests:** `444 passed` (`22.63s`) under dummy video/audio drivers, including 8 new tests in `tests/test_wave_tick_tock.py` and updated `SOUND_NAMES` assertions in `tests/test_sound.py` and `tests/test_rapid_fire.py`.
- **Scope:** Diff (`7 files changed, 295 insertions(+), 6 deletions(-)`) touches only the exact files specified in `spec.md`; `tests/test_wave_counter.py` and `config.json` are untouched.
- **Risk:** Minimal; `tick_tock` reuses `square_sweep` with zero-sample padding, caches via `sound_bytes`, and uses a local `prev_wave` variable in `MainGame.update()` with no state or I/O side effects.
