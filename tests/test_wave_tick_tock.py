"""Tests for job 019-wave-tick-tock: synthesised tick-tock sound on wave changes."""

import gc
import os

import pygame
import pytest

import game.constants as constants
import systems.score
from game.constants import (SOUND_NAMES, SOUND_SAMPLE_RATE, SOUND_VOLUME,
                            STATE_GAME_OVER, STATE_PAUSED, STATE_PLAYING)
from systems.game_loop import MainGame
from systems.sound import sound_bytes

SR = 22050
PEAK = round(SOUND_VOLUME * 32767)
REAL_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.json")


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


def _read_config():
    """Bytes of the real config.json, or None if it doesn't exist."""
    if not os.path.exists(REAL_CONFIG):
        return None
    with open(REAL_CONFIG, "rb") as f:
        return f.read()


@pytest.fixture(autouse=True, scope="module")
def real_config_untouched():
    """Criterion 7: the real config.json is byte-for-byte unchanged by this module."""
    before = _read_config()
    yield
    assert _read_config() == before


@pytest.fixture
def spy(main_game, monkeypatch):
    """``main_game`` with ``sound.play`` replaced by a recorder; yields ``(game, calls)``."""
    calls = []
    monkeypatch.setattr(main_game.sound, "play", lambda name: calls.append(name) or True)
    return main_game, calls


# 1. Constants


def test_constants():
    """Criterion 1: SOUND_TICK_TOCK and SOUND_NAMES have the expected values."""
    assert constants.SOUND_TICK_TOCK == (880, 660, 0.06, 0.04, 0.08)
    assert SOUND_NAMES == ("launch", "explosion", "intercept", "impact",
                           "game_over", "laser", "tick_tock")


# 2. tick_tock waveform structure and pitches


def test_tick_tock_waveform():
    """Criterion 2: tick_tock returns tick + silent gap + tock with expected pitches."""
    from systems.sound import tick_tock

    s = tick_tock(*constants.SOUND_TICK_TOCK, SR)
    n_tick = n(0.06, SR)
    n_gap = n(0.04, SR)
    n_tock = n(0.08, SR)
    assert n_tick == 1323
    assert n_gap == 882
    assert n_tock == 1764

    assert s.typecode == 'h'
    assert len(s) == n_tick + n_gap + n_tock == 3969 == n(0.18, SR)

    tick = s[:n_tick]
    assert abs(tick[0]) == PEAK
    assert max(abs(x) for x in tick) <= PEAK
    assert tick[-1] == 0

    gap = s[n_tick:n_tick + n_gap]
    assert len(gap) == n_gap
    assert all(x == 0 for x in gap)

    tock = s[n_tick + n_gap:]
    assert abs(tock[0]) == PEAK
    assert max(abs(x) for x in tock) <= PEAK
    assert tock[-1] == 0

    sc_tick = sign_changes(tick)
    sc_tock = sign_changes(tock)
    assert 100 <= sc_tick <= 110
    assert 100 <= sc_tock <= 110
    assert (sc_tick / len(tick)) > 1.25 * (sc_tock / len(tock))

    # Also check default sample_rate and volume parameters
    s_default = tick_tock(*constants.SOUND_TICK_TOCK)
    assert s_default == s
    assert SOUND_SAMPLE_RATE == SR


# 3. sound_bytes and SoundSystem integration


@pytest.mark.parametrize("channels", (1, 2))
def test_sound_bytes_tick_tock_length_and_cache(channels):
    """Criterion 3a: sound_bytes builds and caches mono and stereo tick_tock buffers."""
    data = sound_bytes("tick_tock", SR, channels)
    assert isinstance(data, bytes)
    assert len(data) == n(0.18, SR) * 2 * channels
    assert sound_bytes("tick_tock", SR, channels) is data


def test_sound_system_tick_tock_play_and_mute(main_game):
    """Criterion 3b: SoundSystem builds tick_tock, plays it, and respects mute."""
    try:
        pygame.mixer.get_init()
    except NotImplementedError:
        pytest.skip("pygame.mixer is not available in this pygame build")
    game = main_game
    assert "tick_tock" in game.sound.sounds
    assert game.sound.sounds["tick_tock"].get_length() == pytest.approx(0.18, abs=0.02)
    assert game.sound.play("tick_tock") is True
    game.sound.toggle_mute()
    assert game.sound.play("tick_tock") is False


# 4. Plays once on each wave transition during update()


def test_plays_once_on_each_wave_transition(spy):
    """Criterion 4: update() plays tick_tock once each time the wave increases."""
    game, calls = spy
    assert game.game_time == 0.0
    assert game.current_wave() == 1

    for _ in range(59):
        game.update(0.5)
    assert game.game_time == pytest.approx(29.5)
    assert game.current_wave() == 1
    assert calls.count("tick_tock") == 0

    game.update(0.5)
    assert game.game_time == pytest.approx(30.0)
    assert game.current_wave() == 2
    assert calls.count("tick_tock") == 1

    for _ in range(59):
        game.update(0.5)
    assert game.game_time == pytest.approx(59.5)
    assert game.current_wave() == 2
    assert calls.count("tick_tock") == 1

    game.update(0.5)
    assert game.game_time == pytest.approx(60.0)
    assert game.current_wave() == 3
    assert calls.count("tick_tock") == 2

    # Advance to 90.0 (Wave 4)
    for _ in range(60):
        game.update(0.5)
    assert game.game_time == pytest.approx(90.0)
    assert game.current_wave() == 4
    assert calls.count("tick_tock") == 3

    # Advance to 120.0 (Wave 5)
    for _ in range(60):
        game.update(0.5)
    assert game.game_time == pytest.approx(120.0)
    assert game.current_wave() == 5
    assert calls.count("tick_tock") == 4


# 5. Start, restart, pause, and game over do not play tick_tock


def test_start_restart_pause_game_over_no_tick_tock(spy):
    """Criterion 5: start_game, pause/resume, game over, and restart do not play tick_tock."""
    game, calls = spy
    game.start_game()
    assert calls.count("tick_tock") == 0

    game.game_time = 29.9
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    for _ in range(100):
        game.handle_actions({})
        game.draw_start_screen()
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING
    assert calls.count("tick_tock") == 0

    game.update(0.2)
    assert game.game_time == pytest.approx(30.1)
    assert game.current_wave() == 2
    assert calls.count("tick_tock") == 1

    calls.clear()
    for building in game.buildings:
        building.destroy()
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER
    assert "game_over" in calls
    assert calls.count("tick_tock") == 0

    game.handle_actions({"start": True})
    assert game.state == STATE_PLAYING
    assert game.current_wave() == 1
    assert calls.count("tick_tock") == 0


# 6. No wave attribute added and no-audio fallback works across wave changes


def test_no_wave_attribute_added(main_game):
    """Criterion 6a: crossing a wave boundary adds no attribute containing 'wave'."""
    game = main_game
    game.game_time = 29.5
    game.update(1.0)
    assert game.current_wave() == 2
    assert [k for k in vars(game) if "wave" in k.lower()] == []


def test_no_audio_fallback_across_wave_change(monkeypatch, tmp_path):
    """Criterion 6b: wave transition works silently when audio mixer is unavailable."""
    gc.collect()
    pygame.quit()
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))

    def no_init(*args, **kwargs):
        raise pygame.error("no audio")

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    monkeypatch.setattr(pygame.mixer, "init", no_init)
    game = MainGame()
    try:
        assert game.sound.available is False
        game.start_game()
        game.state = STATE_PLAYING
        game.last_spawn_time = float("inf")
        game.game_time = 29.5
        game.update(1.0)
        assert game.current_wave() == 2
    finally:
        del game
        gc.collect()
        pygame.quit()
