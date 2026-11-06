"""Tests for the repeating rapid-fire window (job 015).

A window opens at every whole minute of ``game_time`` from
``RAPID_FIRE_START_TIME`` on, every ``RAPID_FIRE_INTERVAL`` seconds, and lasts
``RAPID_FIRE_DURATION`` seconds: [60, 70), [120, 130), [180, 190), ...
"""

import gc
import os

import pygame
import pytest

import systems.score
from game.constants import (BASE_COOLDOWN_TIME, COLOR_WHITE, DT_DEFAULT,
                            LAUNCHER_RAPID_FIRE_COLOR, RAPID_FIRE_COOLDOWN_TIME,
                            RAPID_FIRE_DURATION, RAPID_FIRE_INTERVAL,
                            RAPID_FIRE_START_TIME, STATE_PAUSED, STATE_PLAYING)
from systems.game_loop import MainGame

FIRE = {"fire_missile": (400, 300)}
REAL_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.json")


def spy(monkeypatch, game):
    """Replace ``game.sound.play`` with a recorder and return its call list."""
    calls = []
    monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)
    return calls


def launches(game, actions=FIRE):
    """Return how many defence missiles one ``handle_actions(actions)`` call launched."""
    before = len(game.defense_missiles)
    game.handle_actions(actions)
    return len(game.defense_missiles) - before


def restart(game):
    """Start a new game on ``game`` and keep it playing with no random spawns."""
    game.start_game()
    game.state = STATE_PLAYING
    game.last_spawn_time = float("inf")


def at_time(game, t):
    """Bring ``game_time`` to about ``t`` through one short ``update()``."""
    game.game_time = t - 0.1
    game.update(0.1)


# 1. Constants


def test_constants():
    assert RAPID_FIRE_INTERVAL == 60.0
    assert RAPID_FIRE_START_TIME == 60.0
    assert RAPID_FIRE_DURATION == 10.0
    assert RAPID_FIRE_COOLDOWN_TIME == 0.1
    assert 0 < RAPID_FIRE_DURATION < RAPID_FIRE_INTERVAL


# 2. Window boundaries across several minutes


@pytest.mark.parametrize("t", [60.0, 69.99, 120.0, 125.0, 129.99, 180.0, 189.99,
                               3600.0, 3605.0])
def test_window_open(main_game, t):
    main_game.game_time = t
    assert main_game.rapid_fire_active() is True


@pytest.mark.parametrize("t", [0.0, 5.0, 9.99, 59.99, 70.0, 100.0, 119.99, 130.0,
                               179.99, 190.0, 3610.0])
def test_window_closed(main_game, t):
    main_game.game_time = t
    assert main_game.rapid_fire_active() is False


# 3. Exactly one on/off pair per minute


def test_one_on_off_pair_per_minute(main_game):
    game = main_game
    restart(game)
    ons, offs, on_frames = [], [], 0
    prev = game.base.rapid_fire
    for _ in range(2000):
        game.update(0.1)
        now = game.base.rapid_fire
        assert now == game.rapid_fire_active()
        if now and not prev:
            ons.append(game.game_time)
        elif prev and not now:
            offs.append(game.game_time)
        if now:
            on_frames += 1
        prev = now
    assert len(ons) == 3
    assert len(offs) == 3
    for t, edge in zip(ons, (60.0, 120.0, 180.0)):
        assert edge <= t <= edge + 0.11
    for t, edge in zip(offs, (70.0, 130.0, 190.0)):
        assert edge <= t <= edge + 0.11
    assert 297 <= on_frames <= 303


# 4. Fast reload in the second and third windows


@pytest.mark.parametrize("start", [120.1, 180.1])
def test_fast_reload_in_later_windows(main_game, start):
    game = main_game
    at_time(game, start)
    game.base.cooldown_time = 0.0

    assert launches(game) == 1
    assert game.base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)

    game.update(0.05)
    assert launches(game) == 0

    total = 0
    for _ in range(20):
        game.update(0.11)
        total += launches(game)
    assert total == 20
    assert game.rapid_fire_active() is True


# 5. Normal reload between windows


@pytest.mark.parametrize("t", [100.0, 150.0])
def test_normal_reload_between_windows(main_game, t):
    game = main_game
    at_time(game, t)
    game.base.cooldown_time = 0.0
    assert launches(game) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME
    game.update(0.2)
    assert launches(game) == 0


# 6. A new window cuts a running slow reload


def test_new_window_cuts_slow_reload(main_game):
    game = main_game
    at_time(game, 119.9)
    game.base.cooldown_time = 0.0
    assert launches(game) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME

    game.update(0.2)  # crosses 120 s
    assert game.base.rapid_fire is True
    assert game.base.cooldown_time <= RAPID_FIRE_COOLDOWN_TIME

    game.update(0.11)
    assert game.base.can_fire() is True
    assert launches(game) == 1
    assert game.base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)


# 7. The short reload finishes after the second window ends


def test_short_reload_finishes_after_second_window(main_game):
    game = main_game
    at_time(game, 129.95)
    game.base.cooldown_time = 0.0
    assert launches(game) == 1

    game.update(0.05)
    assert game.base.rapid_fire is False
    assert game.base.cooldown_time == pytest.approx(0.05)

    game.update(0.06)
    assert game.base.can_fire() is True

    assert launches(game) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME


# 8. Sound follows each window


def test_sound_follows_each_window(main_game, monkeypatch):
    game = main_game
    calls = spy(monkeypatch, game)
    expected = {10.0: "launch", 65.0: "laser", 100.0: "launch",
                125.0: "laser", 150.0: "launch", 185.0: "laser"}
    for t, name in expected.items():
        at_time(game, t)
        game.base.cooldown_time = 0.0
        del calls[:]
        game.handle_actions(FIRE)
        assert calls == [name], t


# 9. Pause freezes a later window


def test_pause_freezes_later_window(main_game):
    game = main_game
    game.game_time = 125.0
    game.update(DT_DEFAULT)
    t = game.game_time
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    game.base.cooldown_time = 0.0
    assert launches(game) == 0
    for _ in range(600):
        game.handle_actions({})
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING
    assert game.game_time == t
    assert game.base.rapid_fire is True
    game.update(DT_DEFAULT)
    assert game.base.rapid_fire is True


# 10. A new game starts the cycle again


def test_new_game_restarts_cycle(main_game):
    game = main_game
    at_time(game, 125.0)
    assert game.base.rapid_fire is True
    game.start_game()
    assert game.game_time == 0.0
    assert game.base.rapid_fire is False
    assert game.rapid_fire_active() is False
    game.state = STATE_PLAYING
    game.last_spawn_time = float("inf")
    at_time(game, 30.0)
    assert game.base.rapid_fire is False
    at_time(game, 60.1)
    assert game.base.rapid_fire is True


# 11. Tower colour in rendered frames


def _frame_tower_pixels(game):
    """Draw the game and return the (body, barrel) centre colours from the screen."""
    game.draw()
    base = game.base
    body = tuple(game.screen.get_at(base.get_bounds().center)[:3])
    barrel = tuple(game.screen.get_at(base.barrel_rect().center)[:3])
    return body, barrel


@pytest.mark.parametrize("t, colour", [
    (125.0, LAUNCHER_RAPID_FIRE_COLOR), (185.0, LAUNCHER_RAPID_FIRE_COLOR),
    (100.0, COLOR_WHITE), (135.0, COLOR_WHITE),
])
def test_frame_tower_colour(main_game, t, colour):
    at_time(main_game, t)
    assert _frame_tower_pixels(main_game) == (colour, colour)


# 12. Long game, no audio, no crash


def test_second_window_no_audio_no_crash(monkeypatch, tmp_path):
    gc.collect()
    pygame.quit()
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))

    def no_init(*args, **kwargs):
        raise pygame.error("no audio")

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    monkeypatch.setattr(pygame.mixer, "init", no_init)
    game = MainGame()
    try:
        game.handle_actions({"start": True})
        game.last_spawn_time = float("inf")
        at_time(game, 119.5)
        for _ in range(120):
            game.handle_actions(FIRE)
            game.update(DT_DEFAULT)
            game.check_collisions()
            game.draw()
        assert game.base.rapid_fire is True
    finally:
        del game
        gc.collect()
        pygame.quit()


# 13. Real config untouched


def test_real_config_untouched(main_game, monkeypatch):
    before = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    game = main_game
    spy(monkeypatch, game)
    at_time(game, 120.1)
    for _ in range(30):
        game.handle_actions(FIRE)
        game.update(0.11)
        game.check_collisions()
    game.score_system.save_high_score()
    after = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    assert before == after
