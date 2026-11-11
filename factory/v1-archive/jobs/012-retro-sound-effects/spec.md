# 012-retro-sound-effects: Retro synthesised sound effects

## Problem
The game makes no sound at all. Firing, explosions, intercepts, building hits and game over
are all silent, so the player gets no audio feedback and the game doesn't feel like an early
arcade game. GAME_DESIGN.md §12 Phase 5 lists "Sound effects (optional)". We want original
8-bit / early-arcade *style* sounds built in code from square waves, noise and pitch sweeps.
No samples, recordings or asset files, and nothing copied from an existing game. The game
must keep working, silently, when there is no audio device or mixer.

## Scope
- **New module `systems/sound.py`.** Plain Python only: `array`, `functools`, `pygame`. No numpy,
  no `pygame.sndarray`, and no `random` module.
  - `square_sweep(start_hz, end_hz, duration, sample_rate=SOUND_SAMPLE_RATE, volume=SOUND_VOLUME)`
    returns an `array.array('h')` of mono signed 16-bit samples.
    - Length `n = round(duration * sample_rate)`.
    - The wave is square: every sample is `+A` or `-A` for the current envelope amplitude `A`.
    - Frequency moves linearly from `start_hz` to `end_hz` over the buffer. Phase is
      accumulated sample by sample so the sweep has no jumps.
    - Envelope: amplitude `peak = round(volume * 32767)` until the last
      `round(SOUND_FADE_TIME * sample_rate)` samples. Over those it fades linearly to 0, and
      the last sample is exactly `0`.
  - `noise_burst(step_hz, duration, sample_rate=SOUND_SAMPLE_RATE, volume=SOUND_VOLUME, seed=SOUND_NOISE_SEED)`
    returns an `array.array('h')`, also of length `round(duration * sample_rate)`.
    - Uses a 15-bit LFSR (linear-feedback shift register, a cheap pseudo-random bit
      generator) starting from `seed`, which must be non-zero.
    - Each output bit is held for about `sample_rate / step_hz` samples as `+A` or `-A`.
      Lower `step_hz` gives a deeper rumble.
    - Envelope decays linearly from `peak` at sample 0 to exactly `0` at the last sample.
    - The output is deterministic: the same arguments give the same samples.
  - `sound_bytes(name, sample_rate, channels)` returns the raw mixer buffer (`bytes`) for one
    of `SOUND_NAMES`.
    - Builds the mono samples from that sound's recipe constant, then repeats each sample
      `channels` times to interleave the channels.
    - Cached with `functools.lru_cache`, so each `(name, rate, channels)` is synthesised only
      once per process.
    - An unknown `name` raises `KeyError`.
  - `pre_init_mixer()` calls
    `pygame.mixer.pre_init(SOUND_SAMPLE_RATE, -16, 1, SOUND_BUFFER_SIZE)`. It never raises:
    it catches `pygame.error`, `NotImplementedError` and `ImportError`.
  - `class SoundSystem`:
    - `__init__()`: if `pygame.mixer.get_init()` is `None`, tries `pygame.mixer.init(...)`
      with the pre-init values. It then reads `(freq, size, channels)` from `get_init()`.
    - If the mixer is up and `size == -16`, it builds `self.sounds[name] =
      pygame.mixer.Sound(buffer=sound_bytes(name, freq, channels))` for every name and sets
      `self.available = True`.
    - Otherwise, or if any of those calls raises `pygame.error`, `NotImplementedError` or
      `ImportError`, it sets `available = False` and `sounds = {}`. It never raises for those
      errors.
    - `self.muted = False` at start.
    - `play(name)`:
      - raises `KeyError` if `name not in SOUND_NAMES`, even when audio is unavailable, so
        typos fail in headless tests;
      - returns `False` without doing anything when muted or unavailable;
      - otherwise calls `self.sounds[name].play()` and returns `True`;
      - returns `False` if that call raises `pygame.error`, which happens after
        `pygame.quit()`.
    - `toggle_mute()` flips `muted` and returns the new value.
- **`MainGame` wiring** (`systems/game_loop.py`):
  - `__init__` calls `pre_init_mixer()` just before `pygame.init()` and sets
    `self.sound = SoundSystem()` after it.
  - Sound events. Each is played at most once per call of the method named:
    - `"launch"`: in `spawn_defense_missile()`, only when a missile is actually launched
      (`can_fire()` was True).
    - `"explosion"`: in `update()`, once if one or more defense missiles detonated that call.
    - `"intercept"`: in `check_collisions()`, once if one or more incoming missiles were
      destroyed by player explosions that call. Scoring is unchanged: still
      `MISSILE_INTERCEPT_POINTS` per missile.
    - `"impact"`: in `check_collisions()`, once if one or more incoming missiles hit a
      building that call.
    - `"game_over"`: in `check_game_over()`, on the transition to `STATE_GAME_OVER` only.
  - `handle_actions()`: a `"toggle_mute"` action calls `self.sound.toggle_mute()` in every
    state. It doesn't affect state transitions or firing in the same call.
  - `start_game()` does not reset `muted`, so mute lasts across restarts within a session.
  - `menu_lines()` gets one more controls line at `mid + 140`, size 36, `COLOR_WHITE`:
    `"M: Mute sound"`, or `"M: Unmute sound"` when muted.
- **Input** (`systems/input_system.py`): `KEYDOWN` with `pygame.K_m` adds
  `actions["toggle_mute"] = True`.
- **Constants**: a new `# Sound` section at the end of `game/constants.py` (see Touch points).
- **README**:
  - a Controls table row `| M | Mute / unmute sound effects |`;
  - one sentence in "Gameplay" saying the sound effects are retro-style and generated in code.
- **Tests**: one new file, `tests/test_sound.py`. Do not edit existing test files.

## Out of scope
- Background music, a start-screen jingle, or a sound when the launcher finishes reloading or
  a click is ignored during cooldown.
- Reading or writing `"sound_enabled"` (or anything else) in `config.json`, or saving mute
  across runs. That is a natural follow-up job. This job does no file I/O.
- A volume slider, per-sound volume settings, or channel/priority management beyond pygame's
  default channels.
- Pausing or stopping sounds that are playing when the game is paused. All sounds are 1.0 s
  or shorter.
- Stereo panning by screen position.
- A HUD mute indicator during play.
- Any change to launcher position, missile trails or collision/score tests. Jobs 009, 010 and
  011 are doing those on other branches. Don't touch `entities/`, `systems/score.py` or
  existing tests.
- Audio files under `assets/`, and GAME_DESIGN.md edits.

## Acceptance criteria
Terms used below:
- `FIRE = {"fire_missile": (400, 300)}`.
- A **spy** is `calls = []` plus `monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)`.
- `PEAK = round(SOUND_VOLUME * 32767)`.
- `n(d, sr) = round(d * sr)`.
- **Sign changes** means the number of sign flips between consecutive non-zero samples.
- Tests that build a `MainGame` patch `systems.score.CONFIG_PATH` first (the `main_game`
  fixture already does this).
- No test may depend on the launcher's position, because job 009 moves it.

1. [test] **Constants.** All of these exist with these values:
   - `SOUND_SAMPLE_RATE == 22050`, `SOUND_BUFFER_SIZE == 512`, `SOUND_VOLUME == 0.25`,
     `SOUND_FADE_TIME == 0.01`;
   - `SOUND_NOISE_SEED` is a non-zero int below `2**15`;
   - `SOUND_LAUNCH_SWEEP == (330, 990, 0.15)`, `SOUND_INTERCEPT_SWEEP == (1200, 2400, 0.08)`,
     `SOUND_GAME_OVER_SWEEP == (440, 55, 1.0)`;
   - `SOUND_EXPLOSION_NOISE == (4000, 0.5)`, `SOUND_IMPACT_NOISE == (1200, 0.35)`;
   - `SOUND_NAMES == ("launch", "explosion", "intercept", "impact", "game_over")`.
2. [test] **Square shape.** `s = square_sweep(440, 440, 0.1, 22050)`:
   - `s.typecode == 'h'` and `len(s) == n(0.1, 22050)`;
   - `abs(s[0]) == PEAK`, `max(abs(x) for x in s) <= PEAK` and `s[-1] == 0`;
   - every sample before the fade (the first `len(s) - round(0.01 * 22050)`) has
     `abs == PEAK`;
   - sign changes across the whole buffer are between 86 and 90.
3. [test] **Pitch sweeps.** For `up = square_sweep(200, 2000, 0.5, 22050)`, the window
   `[3n/5, 4n/5)` has more than 2.5 times as many sign changes as the window `[0, n/5)`.
   For `down = square_sweep(2000, 200, 0.5, 22050)`, the reverse holds. The launch recipe
   rises and the game-over recipe falls, checked the same way on samples built from
   `SOUND_LAUNCH_SWEEP` and `SOUND_GAME_OVER_SWEEP`.
4. [test] **Noise.** `a = noise_burst(4000, 0.5, 22050)`:
   - `len(a) == n(0.5, 22050)`, `max(abs) <= PEAK` and `a[-1] == 0`;
   - each quarter of the buffer has both positive and negative samples;
   - the RMS of the first quarter is more than 2 times the RMS of the last quarter;
   - a second call with the same arguments is equal to `a`;
   - `noise_burst(1200, 0.5, 22050)` has fewer than half the sign changes of `a`;
   - with `seed=SOUND_NOISE_SEED + 1` the result differs from `a`.
5. [test] **No global randomness.** `random.seed(7)` then `st = random.getstate()`. Call
   `square_sweep`, `noise_burst`, `sound_bytes` for every name, and `SoundSystem()`. Then
   `random.getstate() == st`.
6. [test] **Buffer bytes.** For every name in `SOUND_NAMES` and `channels` in `(1, 2)`,
   `len(sound_bytes(name, 22050, channels)) == n(d, 22050) * 2 * channels`, where `d` is that
   recipe's duration. A second identical call returns the same object (`is`), which shows the
   cache works. `sound_bytes("boom", 22050, 1)` raises `KeyError`.
7. [test] **Sounds built under the dummy driver.** Using `main_game` (SDL_AUDIODRIVER=dummy):
   - `game.sound.available is True` and `set(game.sound.sounds) == set(SOUND_NAMES)`;
   - for each sound, `get_length()` is `pytest.approx(d, abs=0.02)`, where `d` is that
     recipe's duration;
   - `game.sound.play("launch") is True`.

   Only if `pygame.mixer` itself is missing from the pygame build, skip with a reason.
8. [test] **No audio, no crash.** Patch `pygame.mixer.get_init` to return `None` and
   `pygame.mixer.init` to raise `pygame.error("no audio")`. Then:
   - `MainGame()` builds, `game.sound.available is False` and `game.sound.sounds == {}`;
   - `play(name)` returns `False` for every name.

   Repeat with both functions raising `NotImplementedError`, and also with
   `pygame.mixer.pre_init` raising `NotImplementedError`. In each case, drive a game through
   start, `FIRE`, 120 frames of `update(DT_DEFAULT)` + `check_collisions()` + `draw()`, then
   destroy all buildings and call `check_game_over()`. No exception is raised and
   `state == STATE_GAME_OVER`.
9. [test] **Sound creation failure.** With the mixer working but `pygame.mixer.Sound` patched
   to raise `pygame.error`, `SoundSystem()` gives `available is False` without raising.
10. [test] **`play()` semantics.** On a `SoundSystem()`, replace `sounds["launch"]` with a fake
    whose `play()` records calls.
    - `play("launch")` returns `True` and the fake is called once.
    - After `toggle_mute()` (which returns `True`), `play("launch")` returns `False` and the
      fake is not called again. `toggle_mute()` again returns `False`.
    - `play("pew")` raises `KeyError`, both when available and with `available = False`.
    - A fake whose `play()` raises `pygame.error` makes `play` return `False`.
11. [test] **Launch.** `main_game` with a spy:
    - `handle_actions(FIRE)` gives `calls == ["launch"]`;
    - a second `handle_actions(FIRE)` straight away (launcher reloading) adds nothing;
    - after `game.state = STATE_PAUSED`, `handle_actions(FIRE)` adds nothing.
12. [test] **Explosion and intercept.** `main_game` with a spy.
    - `handle_actions(FIRE)`, then call `update(DT_DEFAULT)` until `defense_missiles` is
      empty (at most 300 frames). `calls.count("explosion") == 1`, and it was added on the
      same frame the missile was removed or the one before.
    - Then append 3 `IncomingMissile`s, each with its position set to `(400, 300)` and zero
      velocity, and call `check_collisions()` once. `calls.count("intercept") == 1` and the
      score rose by exactly `3 * MISSILE_INTERCEPT_POINTS`.
    - Calling `check_collisions()` again adds no further `"intercept"`.
13. [test] **Impact.** `main_game` with a spy. Place two incoming missiles 5 px inside the
    bounds of two different buildings and call `check_collisions()`. `calls == ["impact"]`.
    A frame with no hit adds nothing.
14. [test] **Game over.** `main_game` with a spy. Mark every building destroyed, then call
    `check_collisions()` and `check_game_over()`. `calls.count("game_over") == 1` and
    `state == STATE_GAME_OVER`. Calling `check_game_over()` again adds nothing.
    `draw_start_screen()`, and `handle_actions({"start": True})` to restart, add no sounds.
15. [test] **Mute key.**
    - Post a `pygame.KEYDOWN` event with `key=pygame.K_m` and call
      `game.input_system.handle_events()`. The result contains `"toggle_mute": True`.
    - In each of `STATE_START`, `STATE_PLAYING`, `STATE_PAUSED` and `STATE_GAME_OVER`,
      `handle_actions({"toggle_mute": True})` flips `game.sound.muted` and leaves `state`
      unchanged.
    - `handle_actions({"toggle_mute": True, "start": True})` from `STATE_START` both mutes and
      starts.
    - `muted` stays `True` after `start_game()`.
16. [test] **Menu line.**
    - On a start-screen game, `menu_lines()` contains `("M: Mute sound", 36, COLOR_WHITE, SCREEN_HEIGHT // 2 + 140)`.
    - After `toggle_mute()` it contains `"M: Unmute sound"` instead, and `"M: Mute sound"`
      is gone.
    - Same on the pause screen.
    - Lines stay at least 30 px apart, in top-to-bottom order.
17. [test] All existing tests pass unchanged. The full suite passes with the README command,
    and the real `config.json` is byte-for-byte unchanged.
18. [visual] **Start screen.** `draw_start_screen()` on a start-screen game. Below
    "ESC: Pause / Resume" and above the yellow "Press SPACE to Start" prompt there is a white
    line "M: Mute sound", in the same font size and centred like the other controls lines.
    It doesn't overlap either neighbour.
19. [visual] **Pause screen, muted.** After `toggle_mute()` with `state = STATE_PAUSED`,
    `draw_start_screen()` shows "M: Unmute sound" in the same place, and nothing else on the
    pause screen moves.

## Touch points
- `systems/sound.py` (new): `square_sweep`, `noise_burst`, `sound_bytes`, `pre_init_mixer`,
  `SoundSystem` (`available`, `sounds`, `muted`, `play`, `toggle_mute`).
- `systems/game_loop.py`:
  - `MainGame.__init__` (mixer pre-init and `self.sound`);
  - `handle_actions` (`"toggle_mute"`);
  - `spawn_defense_missile`, `update`, `check_collisions` and `check_game_over` (one `play`
    call each);
  - `menu_lines` (one new line).
- `systems/input_system.py`: `handle_events` (`K_m` gives `"toggle_mute"`).
- `game/constants.py`, a new `# Sound` section appended at the end of the file to stay clear
  of 009/010 edits:
  - `SOUND_SAMPLE_RATE = 22050`
  - `SOUND_BUFFER_SIZE = 512`
  - `SOUND_VOLUME = 0.25`: peak amplitude as a fraction of full scale
  - `SOUND_FADE_TIME = 0.01`: seconds of fade-out at the end of each square sweep
  - `SOUND_NOISE_SEED`: non-zero 15-bit LFSR seed
  - `SOUND_LAUNCH_SWEEP = (330, 990, 0.15)`: start Hz, end Hz, seconds
  - `SOUND_INTERCEPT_SWEEP = (1200, 2400, 0.08)`
  - `SOUND_GAME_OVER_SWEEP = (440, 55, 1.0)`
  - `SOUND_EXPLOSION_NOISE = (4000, 0.5)`: noise step Hz, seconds
  - `SOUND_IMPACT_NOISE = (1200, 0.35)`
  - `SOUND_NAMES = ("launch", "explosion", "intercept", "impact", "game_over")`
- `README.md`: Controls row and one Gameplay sentence.
- `tests/test_sound.py` (new).

Expected diff: about 130 lines in `systems/sound.py`, 25 in `game_loop.py`, 2 in the input
system, 15 of constants, 3 of README, and 250–300 lines of tests. Use a shared spy fixture, and
a sign-change helper and an RMS helper in the test file.

## Notes for reviewers
- **code:**
  - Synthesis must be original and procedural: square waves, LFSR noise, linear sweeps and
    envelopes only. No audio files are added anywhere (check the diff for `.wav`, `.ogg`,
    `.mp3` or base64 blobs), and no sample tables are pasted in from elsewhere.
  - Sweeps must accumulate phase per sample (`phase += freq / rate`). Computing
    `sin`/`sign(f(t) * t)` directly gives audible glitches and breaks criterion 3.
  - No `random` module in `systems/sound.py`. Tests seed the global RNG for spawn positions,
    and synthesis must not shift it (criterion 5).
  - Samples must be built for the format the mixer actually reports (`get_init()`). SDL can
    change frequency and channels, and `pygame.init()` may have opened the mixer already.
    Only signed 16-bit is supported. Anything else means `available = False`, not garbled
    audio.
  - Catch only `pygame.error`, `NotImplementedError` (pygame's stand-in for a missing
    module) and `ImportError`, not bare `except`. `play()` with an unknown name must still
    raise `KeyError`.
  - Each event is played at most once per call. Three intercepts in one frame give one
    intercept sound and 30 points.
  - Keep `game_loop.py` edits to the listed lines. 009 and 010 are editing the same file
    (`draw()`, missile spawning and the launcher), so avoid reformatting or moving code.
  - Startup cost: `sound_bytes` is cached. Pure-Python synthesis of about 2 s of audio
    should take well under 0.1 s once, not per `MainGame`. Check the test suite doesn't get
    noticeably slower.
- **security:** No file, network or config I/O is added. `config.json`'s `"sound_enabled"`
  key is deliberately not read in this job. Tests patch `CONFIG_PATH` before building a
  `MainGame`.
- **ux:**
  - Sounds confirm what the player did. Launch only plays when a missile really leaves, so
    a click during reload stays silent and doesn't sound like a shot.
  - `SOUND_VOLUME = 0.25` keeps square waves from being harsh. Explosion and impact use
    different noise pitches so a city hit (low rumble) is told apart from your own blast
    (brighter hiss).
  - M mutes in any state, including menus, and mute lasts across restarts in a session.
  - The headless suite can't check how it sounds. A reviewer with speakers should run
    `python3 main.py` and confirm each event is audible, short, not clipped, and has no
    click at the end.
- **ui:** Check frames 18 and 19. The new controls line must fit between the ESC line and
  the prompt with no overlap, in the existing white 36 px style. No HUD changes during play.
