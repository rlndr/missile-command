"""Tests for job 014-wave-counter: wave number derived from play time and shown in the HUD."""

import types

import pytest

import utils.timer
from game.constants import (COLOR_WHITE, COLOR_YELLOW, DT_DEFAULT, HIGH_SCORE_MAX,
                            HUD_MARGIN, SCREEN_WIDTH, STATE_GAME_OVER, STATE_PAUSED,
                            SURVIVAL_POINTS_PER_SECOND)
import game.constants as constants


def _loop_with_fake_clock(game, monkeypatch, frames=10, step=1.0):
    """Run ``start_game_loop()`` for ``frames`` empty frames, each advancing a fake clock by ``step``."""
    clock = [1000.0]
    monkeypatch.setattr(utils.timer, "time", types.SimpleNamespace(time=lambda: clock[0]))
    game.timer.reset()
    calls = [0]

    def fake_events():
        calls[0] += 1
        if calls[0] > frames:
            return {"quit": True}
        clock[0] += step
        return {}

    monkeypatch.setattr(game, "handle_events", fake_events)
    game.start_game_loop()
    assert calls[0] == frames + 1


def _region(screen, x0, y0, w, h):
    """Return the RGB of every pixel in the rect ``(x0, y0, w, h)``."""
    return [tuple(screen.get_at((x, y)))[:3]
            for y in range(y0, y0 + h) for x in range(x0, x0 + w)]


def _rect_pixels(screen, rect):
    """Return the RGB of every pixel inside ``rect``."""
    return _region(screen, rect.x, rect.y, rect.width, rect.height)


def test_constants():
    """Criterion 1: wave constants have the specified values."""
    assert constants.WAVE_DURATION == 30.0
    assert constants.HUD_WAVE_COLOR == COLOR_WHITE
    assert constants.HUD_WAVE_GAP == 24


@pytest.mark.parametrize("game_time, wave", [
    (0.0, 1), (29.99, 1), (30.0, 2), (59.99, 2), (60.0, 3), (299.99, 10), (300.0, 11),
])
def test_wave_boundaries(main_game, game_time, wave):
    """Criterion 2: the wave is ``game_time // 30 + 1`` as an ``int``."""
    main_game.game_time = game_time
    w = main_game.current_wave()
    assert w == wave
    assert type(w) is int


def test_wave_goes_up_through_play(main_game):
    """Criterion 3: ``update()`` advances the wave exactly at 30 s and 60 s."""
    game = main_game
    assert game.current_wave() == 1
    for _ in range(59):
        game.update(0.5)
    assert game.game_time == 29.5
    assert game.current_wave() == 1
    game.update(0.5)
    assert game.game_time == 30.0
    assert game.current_wave() == 2
    for _ in range(60):
        game.update(0.5)
    assert game.game_time == 60.0
    assert game.current_wave() == 3


def test_hud_wave_text(main_game):
    """Criterion 4: the HUD wave text uses thousands separators."""
    game = main_game
    assert game.hud_wave_text() == "WAVE: 1"
    game.game_time = 65.0
    assert game.hud_wave_text() == "WAVE: 3"
    game.game_time = 30000.0
    assert game.hud_wave_text() == "WAVE: 1,001"


def test_no_wave_bonus_or_side_effects(main_game):
    """Criterion 5: crossing a wave boundary gives only the normal survival point."""
    game = main_game
    game.game_time = 29.5
    game.score_system.time_survived = 29.5
    score_before = game.score_system.score
    can_fire_before = game.base.can_fire()
    keys_before = set(vars(game))
    game.update(1.0)
    assert game.current_wave() == 2
    assert game.score_system.score - score_before == SURVIVAL_POINTS_PER_SECOND == 1
    assert game.defense_missiles == []
    assert game.incoming_missiles == []
    assert game.explosions == []
    assert game.base.can_fire() == can_fire_before
    new_keys = set(vars(game)) - keys_before
    assert not [k for k in new_keys if "wave" in k.lower()]
    assert not [k for k in vars(game) if "wave" in k.lower()]
    time_before = game.game_time
    for _ in range(100):
        game.current_wave()
    assert game.game_time == time_before


def test_pause_and_menus_freeze_wave(main_game, monkeypatch):
    """Criterion 6: paused and game-over frames don't advance the wave."""
    game = main_game
    game.game_time = 29.0
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    _loop_with_fake_clock(game, monkeypatch)
    assert game.game_time == 29.0
    assert game.current_wave() == 1
    game.handle_actions({"toggle_pause": True})
    game.update(DT_DEFAULT)
    assert game.current_wave() == 1

    game.state = STATE_GAME_OVER
    game.game_time = 95.0
    _loop_with_fake_clock(game, monkeypatch)
    assert game.game_time == 95.0
    assert game.current_wave() == 4


def test_restart_goes_back_to_wave_one(main_game):
    """Criterion 7: SPACE after game over starts again at wave 1."""
    game = main_game
    game.game_time = 95.0
    assert game.current_wave() == 4
    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER
    game.handle_actions({"start": True})
    assert game.current_wave() == 1
    assert game.hud_wave_text() == "WAVE: 1"


def _assert_layout(score_rect, wave_rect):
    """Check the shared HUD layout rules for one ``draw_hud()`` result."""
    assert score_rect.topright == (SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN)
    assert wave_rect.top == HUD_MARGIN
    assert wave_rect.right == score_rect.left - constants.HUD_WAVE_GAP
    assert wave_rect.width > 0
    assert not wave_rect.colliderect(score_rect)


def test_hud_layout(main_game):
    """Criterion 8: the wave sits left of the score on the same row, also for long values."""
    game = main_game
    _assert_layout(*game.draw_hud())
    game.score_system.score = HIGH_SCORE_MAX
    game.game_time = 30000.0
    score_rect, wave_rect = game.draw_hud()
    _assert_layout(score_rect, wave_rect)
    assert wave_rect.left >= 0


def test_hud_pixels(main_game):
    """Criterion 9: white wave pixels, an empty gap, and a yellow-only score."""
    game = main_game
    game.draw()
    score_rect, wave_rect = game.draw_hud()
    white = constants.HUD_WAVE_COLOR
    assert white in _rect_pixels(game.screen, wave_rect)
    gap = _region(game.screen, wave_rect.right, HUD_MARGIN,
                  score_rect.left - wave_rect.right, score_rect.bottom - HUD_MARGIN)
    assert gap and white not in gap
    score_pixels = _rect_pixels(game.screen, score_rect)
    assert COLOR_YELLOW in score_pixels
    assert white not in score_pixels


def test_hud_follows_wave(main_game):
    """Criterion 10: changing only the wave changes the HUD pixels, not the score rect."""
    game = main_game
    hud = (SCREEN_WIDTH - 300, 0, 300, 50)
    game.score_system.score = 0
    game.game_time = 10.0
    game.draw()
    before = _region(game.screen, *hud)
    score_before, _ = game.draw_hud()
    game.game_time = 35.0
    game.draw()
    after = _region(game.screen, *hud)
    score_after, _ = game.draw_hud()
    assert game.score_system.score == 0
    assert before != after
    assert score_before == score_after


def test_wave_moves_left_with_score(main_game):
    """Criterion 11: a wider score pushes the wave left by exactly the extra width."""
    game = main_game
    game.game_time = 0.0
    game.score_system.score = 0
    score_a, wave_a = game.draw_hud()
    game.score_system.score = 1234567
    score_b, wave_b = game.draw_hud()
    assert wave_a.width == wave_b.width
    assert score_b.width > score_a.width
    assert wave_a.right - wave_b.right == score_b.width - score_a.width
