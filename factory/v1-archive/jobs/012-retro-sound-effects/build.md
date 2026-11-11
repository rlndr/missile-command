STATUS: READY

## Round 1
**Summary** — Added `systems/sound.py`, which builds square-wave pitch sweeps (phase accumulated per sample, with a 10 ms linear fade) and 15-bit LFSR noise bursts (taps x^15+x^14+1, linear decay to 0) in plain Python. It also adds an `lru_cache`d `sound_bytes`, a `pre_init_mixer` that never raises, and `SoundSystem`, which builds sounds for the format `get_init()` reports and falls back to silent when there is no usable mixer. `MainGame` plays launch, explosion, intercept, impact and game_over at most once per call of the listed methods. The M key toggles mute in every state, mute lasts across restarts, and the start and pause menus show "M: Mute sound" / "M: Unmute sound" at `mid + 140`. Added the `# Sound` constants section at the end of `game/constants.py`, plus a README Controls row and a Gameplay sentence.

One addition beyond the spec: pygame 2.6.1 **segfaults** (it does not raise `pygame.error`) when a `Sound` is played after `pygame.quit()` or `pygame.mixer.quit()`. I reproduced this in isolation. So `play()` checks `pygame.mixer.get_init() is None` and returns False before calling `Sound.play()`. It still catches `pygame.error` / `NotImplementedError` / `ImportError` from that call. A test covers playing after `pygame.quit()`.

**Commits**
- `e0ada55 012-retro-sound-effects: synthesised square-wave and LFSR noise sound effects with M to mute`
- `6a7c1bb 012-retro-sound-effects: tests for synthesis, mixer fallbacks, sound events, mute key and menu line`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Constants | `test_constants` | Yes |
| 2 | Square shape | `test_square_shape` (88 sign changes) | Yes |
| 3 | Pitch sweeps | `test_pitch_sweeps_up_and_down`, `test_recipe_sweep_directions`. See note A. | Yes |
| 4 | Noise | `test_noise_burst` | Yes |
| 5 | No global randomness | `test_no_global_randomness` (cache cleared first so synthesis really runs); `test_sound_module_does_not_import_random` | Yes |
| 6 | Buffer bytes | `test_sound_bytes_length_and_cache[*]` (10 cases), `test_sound_bytes_interleaves_channels`, `test_sound_bytes_unknown_name` | Yes |
| 7 | Sounds under dummy driver | `test_sounds_built_under_dummy_driver` (ran, not skipped) | Yes |
| 8 | No audio, no crash | `test_no_audio_no_crash[no-device / missing-mixer / missing-mixer-pre-init]`, `test_pre_init_failure_alone_still_runs` | Yes |
| 9 | Sound creation failure | `test_sound_creation_failure`; also `test_unsupported_sample_format_is_unavailable` (size != -16) | Yes |
| 10 | `play()` semantics | `test_play_semantics`, `test_play_after_pygame_quit_returns_false` | Yes |
| 11 | Launch | `test_launch_only_when_fired` | Yes |
| 12 | Explosion and intercept | `test_explosion_and_intercept` (3 intercepts give 1 sound and +30) | Yes |
| 13 | Impact | `test_impact` | Yes |
| 14 | Game over | `test_game_over` | Yes |
| 15 | Mute key | `test_m_key_gives_toggle_mute`, `test_toggle_mute_in_every_state[*]` (4 states), `test_mute_and_start_together_and_mute_persists` | Yes |
| 16 | Menu line | `test_menu_mute_line[start/paused]` (tuple, swap, 30 px spacing in order) | Yes |
| 17 | Existing tests unchanged, config untouched | Full suite 205 passed (165 existing, timing unchanged at 8.27 s). Module-scoped autouse fixture `real_config_untouched` compares the real `config.json` bytes before and after; `git status` shows `config.json` clean. | Yes |
| 18 | [visual] Start screen | Rendered `draw_start_screen()` headless. White "M: Mute sound" sits centred under "ESC: Pause / Resume" and above the yellow prompt, at the same 36 px size, with clear gaps on both sides. | Yes |
| 19 | [visual] Pause screen, muted | Rendered the pause screen unmuted and muted. It shows "M: Unmute sound" in the same place. A pixel diff of the two frames only differs in rows 431–447 (that one line), so nothing else moves. | Yes |

Note A (criterion 3): "the reverse holds" for the falling sweep is tested as the same `[0, n/5)` vs `[3n/5, 4n/5)` comparison on the time-reversed buffer. A falling sweep is a rising sweep played backwards. On the unreversed buffer the ratio is 2.46, just under 2.5, which is expected for a linear 2000→200 Hz sweep. For the recipes, the game-over sweep passes the 2.5x test on its reversed buffer. It is also checked unreversed (early > 1.5 × late). The launch sweep (330→990 Hz, only 3x in range) cannot reach 2.5x in those windows: the ratio is about 2.0 for any linear sweep. So it is checked as late > 1.5 × early, which still shows it rises.

Without the `game_loop.py` / `input_system.py` changes, 16 of the 40 new tests fail or error. These are the wiring, mute, menu and fallback tests. The synthesis tests depend on the new module, and none of them can be collected without it.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` gives `205 passed in 10.79s`. Synthesis of all five sounds takes about 6 ms at 22050 Hz mono, once per process.

## Round 2
**Summary** — Merged current `main` (009 bottom launcher, 010 enemy exhaust trails, 011 collision/score tests) into the branch. The only conflict was README.md "Gameplay". I kept 009's launcher-tower paragraph word for word and appended the sound sentence at its end. `game_loop.py` and `constants.py` auto-merged. `git diff main` for them now shows only this job's lines: the import, `pre_init_mixer` / `SoundSystem` in `__init__`, `toggle_mute`, the five `play` calls with their flags, the menu line, and the `# Sound` section still last in constants. The merged code reads cleanly, with no moved or reformatted code. No code changes were needed. The criterion-3 check is unchanged, as accepted in review.

**Commits**
- `5761aa1 012-retro-sound-effects: merge main (009, 010, 011); keep 009's launcher wording in README Gameplay and add the sound sentence after it`

**Acceptance criteria** — Same evidence as Round 1, re-run on the merged tree. All 40 tests in `tests/test_sound.py` pass with 009's bottom launcher, and none depend on the launcher's position. For criterion 17, the 251 other tests (main's existing suite, now including 009/010/011) pass unchanged, and `config.json` is clean in `git status`. For 18 and 19, I re-rendered the start screen and the muted pause screen on the merged tree. "M: Mute sound" / "M: Unmute sound" sits between the ESC line and the prompt with no overlap. I also rendered a play frame: bottom launcher, reload bar and exhaust trail all draw normally, with the mixer available under the dummy driver.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` gives `291 passed in 12.56s`.

**Review responses**
- review-human (CHANGES) — merge main and resolve README keeping 009's wording plus the sound sentence: fixed in `5761aa1`.
- review-code nit 1 (README merge conflict): fixed in `5761aa1`, as above.
- review-code nit 2 (`get_init()` guard in `play()`): reviewer agreed no change was needed; kept, because it prevents a pygame 2.6 segfault.
- review-ux nits 1–3 (no HUD mute confirmation, mute doesn't stop a playing sound, M not listed on the game over screen): not changed. Each is out of scope in the spec ("no HUD mute indicator", "no stopping playing sounds", line only on the start/pause menus), and the reviewer marked them as follow-ups.
- review-security, review-ui: PASS, no findings.
