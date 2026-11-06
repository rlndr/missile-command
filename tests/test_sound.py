"""Tests for job 012-retro-sound-effects: synthesised sounds, mixer fallbacks and game wiring."""

import gc
import math
import os
import random

import pygame
import pytest

import systems.score
import systems.sound
from entities import IncomingMissile
from game.constants import (COLOR_WHITE, DT_DEFAULT, MISSILE_INTERCEPT_POINTS,
                            SCREEN_HEIGHT, SOUND_BUFFER_SIZE, SOUND_EXPLOSION_NOISE,
                            SOUND_FADE_TIME, SOUND_GAME_OVER_SWEEP, SOUND_IMPACT_NOISE,
                            SOUND_INTERCEPT_SWEEP, SOUND_LASER_SWEEP, SOUND_LAUNCH_SWEEP,
                            SOUND_NAMES,
                            SOUND_NOISE_SEED, SOUND_SAMPLE_RATE, SOUND_VOLUME,
                            STATE_GAME_OVER, STATE_PAUSED, STATE_PLAYING, STATE_START)
from systems.game_loop import MainGame
from systems.sound import (SoundSystem, noise_burst, pre_init_mixer, sound_bytes,
                           square_sweep)

Vector2 = pygame.math.Vector2
FIRE = {"fire_missile": (400, 300)}
PEAK = round(SOUND_VOLUME * 32767)
SR = 22050
REAL_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.json")
DURATIONS = {
    "launch": SOUND_LAUNCH_SWEEP[2],
    "explosion": SOUND_EXPLOSION_NOISE[1],
    "intercept": SOUND_INTERCEPT_SWEEP[2],
    "impact": SOUND_IMPACT_NOISE[1],
    "game_over": SOUND_GAME_OVER_SWEEP[2],
    "laser": SOUND_LASER_SWEEP[2],
}


def n(d, sr):
    """Expected sample count for ``d`` seconds at ``sr`` Hz."""
    return round(d * sr)


def sign_changes(samples):
    """Count sign flips between consecutive non-zero samples."""
    flips, prev = 0, 0
    for x in samples:
        if x == 0:
            continue
        if prev and (x > 0) != (prev > 0):
            flips += 1
        prev = x
    return flips


def rms(samples):
    """Root mean square of ``samples``."""
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def _read_config():
    """Bytes of the real config.json, or None if it doesn't exist."""
    if not os.path.exists(REAL_CONFIG):
        return None
    with open(REAL_CONFIG, "rb") as f:
        return f.read()


@pytest.fixture(autouse=True, scope="module")
def real_config_untouched():
    """Criterion 17: the real config.json is byte-for-byte unchanged by this module."""
    before = _read_config()
    yield
    assert _read_config() == before


@pytest.fixture
def spy(main_game, monkeypatch):
    """``main_game`` with ``sound.play`` replaced by a recorder; yields ``(game, calls)``."""
    calls = []
    monkeypatch.setattr(main_game.sound, "play", lambda name: calls.append(name) or True)
    return main_game, calls


@pytest.fixture
def mixer():
    """Initialise pygame (and its mixer) the way ``MainGame`` does; quit afterwards."""
    gc.collect()
    pre_init_mixer()
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def start_game_factory(monkeypatch, tmp_path):
    """Return a factory for a ``MainGame()`` on the start screen, isolated from config.json."""
    gc.collect()
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    made = []

    def make():
        game = MainGame()
        made.append(game)
        return game

    yield make
    made.clear()
    gc.collect()
    pygame.quit()


class FakeSound:
    """Stand-in for ``pygame.mixer.Sound`` that records ``play()`` calls."""

    def __init__(self, error=None):
        self.plays = 0
        self.error = error

    def play(self):
        """Record the call, or raise the configured error."""
        self.plays += 1
        if self.error:
            raise self.error


# 1. Constants


def test_constants():
    assert SOUND_SAMPLE_RATE == 22050
    assert SOUND_BUFFER_SIZE == 512
    assert SOUND_VOLUME == 0.25
    assert SOUND_FADE_TIME == 0.01
    assert isinstance(SOUND_NOISE_SEED, int) and 0 < SOUND_NOISE_SEED < 2 ** 15
    assert SOUND_LAUNCH_SWEEP == (330, 990, 0.15)
    assert SOUND_INTERCEPT_SWEEP == (1200, 2400, 0.08)
    assert SOUND_GAME_OVER_SWEEP == (440, 55, 1.0)
    assert SOUND_EXPLOSION_NOISE == (4000, 0.5)
    assert SOUND_IMPACT_NOISE == (1200, 0.35)
    assert SOUND_NAMES == ("launch", "explosion", "intercept", "impact", "game_over",
                           "laser")


# 2-3. Square sweeps


def test_square_shape():
    s = square_sweep(440, 440, 0.1, SR)
    assert s.typecode == 'h'
    assert len(s) == n(0.1, SR)
    assert abs(s[0]) == PEAK
    assert max(abs(x) for x in s) <= PEAK
    assert s[-1] == 0
    body = len(s) - round(0.01 * SR)
    assert all(abs(x) == PEAK for x in s[:body])
    assert 86 <= sign_changes(s) <= 90


def _windows(samples):
    """Sign changes in the windows ``[0, n/5)`` and ``[3n/5, 4n/5)``."""
    size = len(samples)
    early = sign_changes(samples[:size // 5])
    late = sign_changes(samples[3 * size // 5:4 * size // 5])
    return early, late


def test_pitch_sweeps_up_and_down():
    early, late = _windows(square_sweep(200, 2000, 0.5, SR))
    assert late > 2.5 * early
    # "The reverse holds": a falling sweep is a rising one played backwards,
    # so the same windows of the time-reversed buffer show the same ratio.
    down = square_sweep(2000, 200, 0.5, SR)
    early, late = _windows(down[::-1])
    assert late > 2.5 * early


def test_recipe_sweep_directions():
    # Launch only spans 330-990 Hz (3x), so its windows differ by about 2x;
    # the 2.5x margin is only reachable for the wider game-over drop.
    early, late = _windows(square_sweep(*SOUND_LAUNCH_SWEEP, SR))
    assert late > 1.5 * early
    early, late = _windows(square_sweep(*SOUND_GAME_OVER_SWEEP, SR)[::-1])
    assert late > 2.5 * early
    early, late = _windows(square_sweep(*SOUND_GAME_OVER_SWEEP, SR))
    assert early > 1.5 * late


# 4. Noise


def test_noise_burst():
    a = noise_burst(4000, 0.5, SR)
    assert a.typecode == 'h'
    assert len(a) == n(0.5, SR)
    assert max(abs(x) for x in a) <= PEAK
    assert a[-1] == 0
    q = len(a) // 4
    quarters = [a[i * q:(i + 1) * q] for i in range(4)]
    for part in quarters:
        assert any(x > 0 for x in part) and any(x < 0 for x in part)
    assert rms(quarters[0]) > 2 * rms(quarters[3])
    assert noise_burst(4000, 0.5, SR) == a
    assert sign_changes(noise_burst(1200, 0.5, SR)) < sign_changes(a) / 2
    assert noise_burst(4000, 0.5, SR, seed=SOUND_NOISE_SEED + 1) != a


# 5. No global randomness


def test_no_global_randomness(mixer):
    random.seed(7)
    st = random.getstate()
    square_sweep(330, 990, 0.15)
    noise_burst(4000, 0.5)
    sound_bytes.cache_clear()
    for name in SOUND_NAMES:
        sound_bytes(name, SR, 1)
    SoundSystem()
    assert random.getstate() == st


def test_sound_module_does_not_import_random():
    assert not hasattr(systems.sound, "random")
    with open(systems.sound.__file__) as f:
        source = f.read()
    assert "import random" not in source and "sndarray" not in source
    assert "numpy" not in source


# 6. Buffer bytes


@pytest.mark.parametrize("channels", [1, 2])
@pytest.mark.parametrize("name", SOUND_NAMES)
def test_sound_bytes_length_and_cache(name, channels):
    data = sound_bytes(name, SR, channels)
    assert isinstance(data, bytes)
    assert len(data) == n(DURATIONS[name], SR) * 2 * channels
    assert sound_bytes(name, SR, channels) is data


def test_sound_bytes_interleaves_channels():
    mono = sound_bytes("launch", SR, 1)
    stereo = sound_bytes("launch", SR, 2)
    assert stereo[:4] == mono[:2] * 2
    assert stereo[-4:] == mono[-2:] * 2


def test_sound_bytes_unknown_name():
    with pytest.raises(KeyError):
        sound_bytes("boom", SR, 1)


# 7. Dummy driver


def test_sounds_built_under_dummy_driver(main_game):
    try:
        pygame.mixer.get_init()
    except NotImplementedError:
        pytest.skip("pygame.mixer is not available in this pygame build")
    sound = main_game.sound
    assert sound.available is True
    assert set(sound.sounds) == set(SOUND_NAMES)
    for name, snd in sound.sounds.items():
        assert snd.get_length() == pytest.approx(DURATIONS[name], abs=0.02)
    assert sound.play("launch") is True


# 8-9. Fallbacks


def _raise(exc):
    """Return a function that raises ``exc`` whatever it is called with."""
    def fail(*args, **kwargs):
        raise exc
    return fail


NO_AUDIO_CASES = {
    "no-device": {"get_init": lambda: None, "init": _raise(pygame.error("no audio"))},
    "missing-mixer": {"get_init": _raise(NotImplementedError()),
                      "init": _raise(NotImplementedError())},
    "missing-mixer-pre-init": {"get_init": _raise(NotImplementedError()),
                               "init": _raise(NotImplementedError()),
                               "pre_init": _raise(NotImplementedError())},
}


def _drive_to_game_over(game):
    """Start, fire, run 120 frames, then destroy the city and end the game."""
    game.handle_actions({"start": True})
    game.last_spawn_time = 0.0
    game.handle_actions(FIRE)
    for _ in range(120):
        game.update(DT_DEFAULT)
        game.check_collisions()
        game.draw()
    for building in game.buildings:
        building.destroy()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER


@pytest.mark.parametrize("case", sorted(NO_AUDIO_CASES))
def test_no_audio_no_crash(case, start_game_factory, monkeypatch):
    random.seed(0)
    pygame.quit()
    for attr, fn in NO_AUDIO_CASES[case].items():
        monkeypatch.setattr(pygame.mixer, attr, fn)
    game = start_game_factory()
    assert game.sound.available is False
    assert game.sound.sounds == {}
    for name in SOUND_NAMES:
        assert game.sound.play(name) is False
    _drive_to_game_over(game)


def test_pre_init_failure_alone_still_runs(start_game_factory, monkeypatch):
    random.seed(0)
    monkeypatch.setattr(pygame.mixer, "pre_init", _raise(NotImplementedError()))
    pre_init_mixer()
    game = start_game_factory()
    _drive_to_game_over(game)


def test_unsupported_sample_format_is_unavailable(mixer, monkeypatch):
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (22050, 8, 1))
    sound = SoundSystem()
    assert sound.available is False and sound.sounds == {}


def test_sound_creation_failure(mixer, monkeypatch):
    monkeypatch.setattr(pygame.mixer, "Sound", _raise(pygame.error("bad buffer")))
    sound = SoundSystem()
    assert sound.available is False
    assert sound.sounds == {}


# 10. play() semantics


def test_play_semantics(mixer):
    sound = SoundSystem()
    fake = FakeSound()
    sound.sounds["launch"] = fake
    sound.available = True
    assert sound.play("launch") is True
    assert fake.plays == 1
    assert sound.toggle_mute() is True
    assert sound.play("launch") is False
    assert fake.plays == 1
    assert sound.toggle_mute() is False
    with pytest.raises(KeyError):
        sound.play("pew")
    sound.available = False
    with pytest.raises(KeyError):
        sound.play("pew")
    sound.available = True
    sound.sounds["launch"] = FakeSound(error=pygame.error("mixer not initialized"))
    assert sound.play("launch") is False


def test_play_after_pygame_quit_returns_false(mixer):
    sound = SoundSystem()
    pygame.quit()
    if sound.available:
        assert sound.play("launch") is False


# 11-14. Game events


def test_launch_only_when_fired(spy):
    game, calls = spy
    game.handle_actions(FIRE)
    assert calls == ["launch"]
    game.handle_actions(FIRE)
    assert calls == ["launch"]
    game.state = STATE_PAUSED
    game.handle_actions(FIRE)
    assert calls == ["launch"]


def _park(game, x, y):
    """Append an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position, missile.velocity = Vector2(x, y), Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def test_explosion_and_intercept(spy):
    game, calls = spy
    game.handle_actions(FIRE)
    calls.clear()
    added_on = None
    for frame in range(300):
        before = len(calls)
        game.update(DT_DEFAULT)
        if "explosion" in calls[before:]:
            added_on = frame
        if not game.defense_missiles:
            removed_on = frame
            break
    else:
        pytest.fail("defense missile never removed")
    assert calls.count("explosion") == 1
    assert removed_on - added_on in (0, 1)

    score = game.score_system.score
    for _ in range(3):
        _park(game, 400, 300)
    game.check_collisions()
    assert calls.count("intercept") == 1
    assert game.score_system.score - score == 3 * MISSILE_INTERCEPT_POINTS
    game.check_collisions()
    assert calls.count("intercept") == 1


def test_impact(spy):
    game, calls = spy
    first, second = game.buildings[0], game.buildings[1]
    for building in (first, second):
        _park(game, building.position.x + 5, building.position.y + 5)
    game.check_collisions()
    assert calls == ["impact"]
    game.check_collisions()
    assert calls == ["impact"]


def test_game_over(spy):
    game, calls = spy
    for building in game.buildings:
        building.destroy()
    game.check_collisions()
    game.check_game_over()
    assert calls.count("game_over") == 1
    assert game.state == STATE_GAME_OVER
    game.check_game_over()
    assert calls.count("game_over") == 1
    count = len(calls)
    game.draw_start_screen()
    game.handle_actions({"start": True})
    assert game.state == STATE_PLAYING
    assert len(calls) == count


# 15-16. Mute key and menu line


def test_m_key_gives_toggle_mute(main_game):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    actions = main_game.input_system.handle_events()
    assert actions.get("toggle_mute") is True


@pytest.mark.parametrize("state", [STATE_START, STATE_PLAYING, STATE_PAUSED, STATE_GAME_OVER])
def test_toggle_mute_in_every_state(main_game, state):
    main_game.state = state
    main_game.handle_actions({"toggle_mute": True})
    assert main_game.sound.muted is True
    assert main_game.state == state
    main_game.handle_actions({"toggle_mute": True})
    assert main_game.sound.muted is False
    assert main_game.state == state


def test_mute_and_start_together_and_mute_persists(main_game):
    main_game.state = STATE_START
    main_game.handle_actions({"toggle_mute": True, "start": True})
    assert main_game.sound.muted is True
    assert main_game.state == STATE_PLAYING
    main_game.start_game()
    assert main_game.sound.muted is True


def _texts(game):
    """Texts of the current ``menu_lines()``."""
    return [line[0] for line in game.menu_lines()]


@pytest.mark.parametrize("state", [STATE_START, STATE_PAUSED])
def test_menu_mute_line(main_game, state):
    main_game.state = state
    mid = SCREEN_HEIGHT // 2
    assert ("M: Mute sound", 36, COLOR_WHITE, mid + 140) in main_game.menu_lines()
    assert "M: Unmute sound" not in _texts(main_game)
    main_game.sound.toggle_mute()
    assert ("M: Unmute sound", 36, COLOR_WHITE, mid + 140) in main_game.menu_lines()
    assert "M: Mute sound" not in _texts(main_game)
    ys = [line[3] for line in main_game.menu_lines()]
    assert all(b - a >= 30 for a, b in zip(ys, ys[1:]))
