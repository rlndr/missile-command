"""Tests for the rapid-fire launcher window (job 013).

After ``RAPID_FIRE_START_TIME`` seconds of play the launcher turns red for
``RAPID_FIRE_DURATION`` seconds, reloads in ``RAPID_FIRE_COOLDOWN_TIME`` and
plays the ``"laser"`` sound on each shot.
"""

import gc
import os

import pygame
import pytest

import systems.score
from entities.base import DefensiveBase
from game.constants import (BASE_COOLDOWN_TIME, COLOR_GRAY, COLOR_RED, COLOR_WHITE,
                            DT_DEFAULT, LAUNCHER_RAPID_FIRE_COLOR, RAPID_FIRE_COOLDOWN_TIME,
                            RAPID_FIRE_DURATION, RAPID_FIRE_START_TIME, SCREEN_HEIGHT,
                            SCREEN_WIDTH, SOUND_LASER_SWEEP, SOUND_NAMES, SOUND_VOLUME,
                            STATE_PAUSED, STATE_PLAYING)
from systems.game_loop import MainGame
from systems.sound import sound_bytes, square_sweep

FIRE = {"fire_missile": (400, 300)}
REAL_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.json")


def spy(monkeypatch, game):
    """Replace ``game.sound.play`` with a recorder and return its call list."""
    calls = []
    monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)
    return calls


def enter_window(game):
    """Move play time from just before the window to about 60.1 s via ``update()``."""
    game.game_time = 59.9
    game.update(0.2)


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
    assert RAPID_FIRE_START_TIME == 60.0
    assert RAPID_FIRE_DURATION == 10.0
    assert RAPID_FIRE_COOLDOWN_TIME == 0.1
    assert LAUNCHER_RAPID_FIRE_COLOR == COLOR_RED
    assert SOUND_LASER_SWEEP == (1800, 300, 0.08)
    assert SOUND_NAMES == ("launch", "explosion", "intercept", "impact", "game_over",
                           "laser")


# 2. Window boundaries


@pytest.mark.parametrize("t, expected", [
    (0.0, False), (59.99, False), (70.0, False),
    (60.0, True), (65.0, True), (69.99, True),
])
def test_window_boundaries(main_game, t, expected):
    main_game.game_time = t
    assert main_game.rapid_fire_active() is expected


# 3. The launcher follows the window


def test_launcher_follows_window(main_game):
    game = main_game
    assert game.base.rapid_fire is False
    enter_window(game)
    assert game.base.rapid_fire is True
    assert game.base.rapid_fire == game.rapid_fire_active()
    game.update(DT_DEFAULT)
    assert game.base.rapid_fire == game.rapid_fire_active()
    game.game_time = 69.9
    game.update(0.2)
    assert game.base.rapid_fire is False
    assert game.base.rapid_fire == game.rapid_fire_active()


# 4. Fast reload during the window


def test_fast_reload_in_window(main_game):
    game = main_game
    enter_window(game)
    game.base.cooldown_time = 0.0

    assert launches(game) == 1
    assert game.base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)

    game.update(0.05)
    assert launches(game) == 0

    game.update(0.06)
    assert launches(game) == 1

    total = 0
    for _ in range(20):
        game.update(0.11)
        total += launches(game)
    assert game.rapid_fire_active() is True
    assert total == 20


# 5. Normal reload outside the window


def test_normal_reload_outside_window(main_game):
    game = main_game
    at_time(game, 10.0)
    assert launches(game) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME
    game.update(0.2)
    assert launches(game) == 0


def test_normal_reload_after_window(main_game):
    game = main_game
    enter_window(game)
    game.base.cooldown_time = 0.0
    assert launches(game) == 1  # a rapid shot with its 0.1 s reload
    game.game_time = 69.9
    game.update(0.2)
    game.update(0.2)
    assert game.base.rapid_fire is False
    assert launches(game) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME


def test_window_end_mid_reload_finishes_short_reload(main_game):
    game = main_game
    game.game_time = 69.95
    game.update(0.01)
    game.base.cooldown_time = 0.0
    assert launches(game) == 1
    game.update(0.05)  # window closes while the 0.1 s reload is running
    assert game.base.rapid_fire is False
    assert game.base.cooldown_time == pytest.approx(0.05)
    game.update(0.06)
    assert game.base.can_fire() is True


# 6. Running reload is cut short on entry


def test_running_reload_cut_short():
    base = DefensiveBase()
    base.reset()
    base.start_cooldown()
    assert base.cooldown_time == BASE_COOLDOWN_TIME
    base.set_rapid_fire(True)
    assert base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)
    assert base.cooldown_length == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)
    assert 0.0 <= base.reload_progress() <= 1.0
    base.update(0.1)
    assert base.can_fire() is True
    assert base.reload_progress() == 1.0


def test_short_reload_left_alone_on_entry():
    base = DefensiveBase()
    base.reset()
    base.cooldown_time = 0.05
    base.set_rapid_fire(True)
    assert base.cooldown_time == 0.05


def test_switching_off_keeps_running_reload():
    base = DefensiveBase()
    base.reset()
    base.set_rapid_fire(True)
    base.start_cooldown()
    base.set_rapid_fire(False)
    assert base.rapid_fire is False
    assert base.cooldown_time == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)
    assert base.cooldown_length == pytest.approx(RAPID_FIRE_COOLDOWN_TIME)


def test_start_cooldown_offline_does_nothing():
    base = DefensiveBase()
    base.reset()
    base.set_rapid_fire(True)
    base.is_active = False
    base.start_cooldown()
    assert base.cooldown_time == 0.0
    assert base.reload_progress() == 0.0


# 7. Reload bar uses the current reload length


def test_reload_progress_uses_current_length():
    base = DefensiveBase()
    base.reset()
    base.set_rapid_fire(True)
    base.start_cooldown()
    assert base.reload_progress() == 0.0
    base.update(0.05)
    assert base.reload_progress() == pytest.approx(0.5)
    assert base.cooldown_ratio == pytest.approx(0.5)

    base.set_rapid_fire(False)
    base.reset()
    base.start_cooldown()
    assert base.cooldown_length == BASE_COOLDOWN_TIME
    base.update(0.375)
    assert base.reload_progress() == pytest.approx(0.25)
    assert base.cooldown_ratio == pytest.approx(0.75)


# 8. Reset clears rapid fire


def test_init_defaults():
    base = DefensiveBase()
    assert base.rapid_fire is False
    assert base.cooldown_length == BASE_COOLDOWN_TIME


def test_reset_clears_rapid_fire():
    base = DefensiveBase()
    base.set_rapid_fire(True)
    base.reset()
    assert base.rapid_fire is False
    assert base.cooldown_length == BASE_COOLDOWN_TIME
    assert base.can_fire() is True


def test_new_game_clears_window(main_game):
    game = main_game
    enter_window(game)
    assert game.base.rapid_fire is True
    game.start_game()
    assert game.base.rapid_fire is False
    assert game.rapid_fire_active() is False
    assert game.game_time == 0.0


# 9. Pause freezes the window


def test_pause_freezes_window(main_game):
    game = main_game
    game.game_time = 65.0
    game.update(DT_DEFAULT)
    t = game.game_time
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    game.base.cooldown_time = 0.0
    assert launches(game) == 0
    for _ in range(600):
        game.handle_actions({})
    assert game.game_time == t
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING
    assert game.game_time == t
    assert game.base.rapid_fire is True
    game.update(DT_DEFAULT)
    assert game.base.rapid_fire is True


# 10. Laser sound on rapid-fire shots


def test_laser_sound_on_rapid_shots(main_game, monkeypatch):
    game = main_game
    calls = spy(monkeypatch, game)
    at_time(game, 10.0)
    game.handle_actions(FIRE)
    assert calls == ["launch"]

    restart(game)
    enter_window(game)
    game.base.cooldown_time = 0.0
    del calls[:]
    game.handle_actions(FIRE)
    assert calls == ["laser"]

    game.update(0.05)
    game.handle_actions(FIRE)
    assert calls == ["laser"]

    game.update(0.06)
    game.state = STATE_PAUSED
    game.handle_actions(FIRE)
    assert calls == ["laser"]


# 11. Laser sound is synthesised like the others


def _sign_changes(samples):
    """Count sign flips between consecutive non-zero samples."""
    flips, prev = 0, 0
    for x in samples:
        if x == 0:
            continue
        if prev and (x > 0) != (prev > 0):
            flips += 1
        prev = x
    return flips


@pytest.mark.parametrize("channels", (1, 2))
def test_laser_bytes_length(channels):
    data = sound_bytes("laser", 22050, channels)
    assert len(data) == round(0.08 * 22050) * 2 * channels


def test_laser_sweep_shape():
    s = square_sweep(*SOUND_LASER_SWEEP, 22050)
    n = len(s)
    assert abs(s[0]) == round(SOUND_VOLUME * 32767)
    assert s[-1] == 0
    early = _sign_changes(s[0:n // 5])
    late = _sign_changes(s[3 * n // 5:4 * n // 5])
    assert early > 1.5 * late
    assert SOUND_LASER_SWEEP[2] < RAPID_FIRE_COOLDOWN_TIME


# 12. Laser sound respects mute and no-audio


def test_laser_sound_built_and_muted(main_game):
    try:
        pygame.mixer.get_init()
    except NotImplementedError:
        pytest.skip("pygame.mixer is not available in this pygame build")
    sound = main_game.sound
    assert "laser" in sound.sounds
    assert sound.sounds["laser"].get_length() == pytest.approx(0.08, abs=0.02)
    assert sound.play("laser") is True
    sound.toggle_mute()
    assert sound.play("laser") is False


def test_laser_no_audio_no_crash(monkeypatch, tmp_path):
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
        assert game.sound.play("laser") is False
        game.handle_actions({"start": True})
        game.last_spawn_time = float("inf")
        enter_window(game)
        assert game.base.rapid_fire is True
        for _ in range(120):
            game.handle_actions(FIRE)
            game.update(DT_DEFAULT)
            game.check_collisions()
            game.draw()
    finally:
        del game
        gc.collect()
        pygame.quit()


# 13. Tower colour from a rendered surface


def _tower_pixels(base):
    """Draw ``base`` on a black screen-sized surface; return (body, barrel) centre colours."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill((0, 0, 0))
    base.draw_base(surface)
    body = surface.get_at(base.get_bounds().center)[:3]
    barrel = surface.get_at(base.barrel_rect().center)[:3]
    return tuple(body), tuple(barrel)


def test_tower_colour_follows_rapid_fire():
    base = DefensiveBase()
    base.reset()
    assert _tower_pixels(base) == (COLOR_WHITE, COLOR_WHITE)
    base.set_rapid_fire(True)
    assert _tower_pixels(base) == (LAUNCHER_RAPID_FIRE_COLOR, LAUNCHER_RAPID_FIRE_COLOR)
    base.set_rapid_fire(False)
    assert _tower_pixels(base) == (COLOR_WHITE, COLOR_WHITE)
    base.set_rapid_fire(True)
    base.is_active = False
    body, _ = _tower_pixels(base)
    assert body == COLOR_GRAY


def test_game_frame_tower_red_in_window(main_game):
    game = main_game
    enter_window(game)
    game.draw()
    base = game.base
    assert tuple(game.screen.get_at(base.get_bounds().center)[:3]) == LAUNCHER_RAPID_FIRE_COLOR
    assert tuple(game.screen.get_at(base.barrel_rect().center)[:3]) == LAUNCHER_RAPID_FIRE_COLOR
    game.game_time = 69.9
    game.update(0.2)
    game.draw()
    assert tuple(game.screen.get_at(base.get_bounds().center)[:3]) == COLOR_WHITE


# 14. Real config untouched


def test_real_config_untouched(main_game, monkeypatch):
    before = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    game = main_game
    spy(monkeypatch, game)
    enter_window(game)
    for _ in range(30):
        game.handle_actions(FIRE)
        game.update(0.11)
        game.check_collisions()
    game.score_system.save_high_score()
    after = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    assert before == after
