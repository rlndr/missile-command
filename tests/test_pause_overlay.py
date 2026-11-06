"""Tests for job 017-pause-overlay: pause dims the frozen scene and lists working keys."""

import types

import pygame
import pytest

import utils.timer
from entities import IncomingMissile
from game.constants import (COLOR_BLACK, COLOR_RED, COLOR_WHITE, COLOR_YELLOW,
                            PAUSE_OVERLAY_ALPHA, PAUSE_OVERLAY_COLOR, SCREEN_HEIGHT,
                            STATE_GAME_OVER, STATE_PAUSED, STATE_PLAYING, STATE_START)

Vector2 = pygame.math.Vector2
MID = SCREEN_HEIGHT // 2
SKY, GROUND, TOWER, MISSILE = (20, 20), (5, 590), (400, 555), (100, 200)
SAMPLES = (SKY, GROUND, TOWER, MISSILE)
PAUSE = {"toggle_pause": True}


def _park(game, x, y):
    """Append an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position, missile.velocity = Vector2(x, y), Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def _px(game, point):
    """Return the RGB triple of ``game.screen`` at ``point``."""
    return tuple(game.screen.get_at(point))[:3]


def _dimmed(colour):
    """Return ``colour`` as it should look under the pause overlay."""
    keep = (255 - PAUSE_OVERLAY_ALPHA) / 255
    return tuple(round(ch * keep) for ch in colour)


def _assert_dimmed(actual, original):
    """Assert each channel of ``actual`` is within 2 of Dimmed(``original``)."""
    expected = _dimmed(original)
    assert all(abs(a - e) <= 2 for a, e in zip(actual, expected)), (actual, expected)


def _has_colour(game, rect, colour):
    """Return True if any pixel of ``game.screen`` inside ``rect`` is exactly ``colour``."""
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            if tuple(game.screen.get_at((x, y)))[:3] == colour:
                return True
    return False


def _texts(game):
    """Return just the text of each ``menu_lines()`` row."""
    return [line[0] for line in game.menu_lines()]


def _pause_lines(score_text, mute_text):
    """Return the expected pause ``menu_lines()`` table."""
    return [
        ("PAUSED", 48, COLOR_WHITE, MID - 120),
        (score_text, 36, COLOR_YELLOW, MID - 30),
        ("Controls:", 36, COLOR_WHITE, MID + 80),
        ("ESC: Resume", 36, COLOR_WHITE, MID + 110),
        (mute_text, 36, COLOR_WHITE, MID + 140),
        ("Press ESC to Resume", 48, COLOR_YELLOW, MID + 190),
    ]


@pytest.fixture
def paused_frame(main_game):
    """Return ``(game, play_pixels)``: one play frame drawn, then paused and redrawn."""
    _park(main_game, *MISSILE)
    main_game.draw()
    play = {point: _px(main_game, point) for point in SAMPLES}
    main_game.handle_actions(PAUSE)
    assert main_game.state == STATE_PAUSED
    main_game.draw_start_screen()
    return main_game, play


# Criterion 1
def test_constants():
    """The overlay is black at alpha 160."""
    assert PAUSE_OVERLAY_COLOR == COLOR_BLACK
    assert PAUSE_OVERLAY_ALPHA == 160


# Criterion 2
def test_pause_dims_live_scene(paused_frame):
    """Every sample point is the dimmed play pixel, and the scene isn't a flat fill."""
    game, play = paused_frame
    for point in SAMPLES:
        _assert_dimmed(_px(game, point), play[point])
    _assert_dimmed(_px(game, MISSILE), COLOR_RED)
    sky = _px(game, SKY)
    for point in (GROUND, TOWER, MISSILE):
        assert _px(game, point) != sky, point


# Criterion 3
def test_text_on_top_of_overlay(paused_frame):
    """Header, mute line and prompt have full-brightness pixels."""
    game, _ = paused_frame
    assert _has_colour(game, pygame.Rect(300, MID - 140, 200, 40), COLOR_WHITE)
    assert _has_colour(game, pygame.Rect(250, MID + 125, 300, 30), COLOR_WHITE)
    assert _has_colour(game, pygame.Rect(200, MID + 170, 400, 40), COLOR_YELLOW)


# Criterion 4
def test_exact_pause_lines(main_game):
    """The pause screen returns exactly the six-row table, mute line following the state."""
    main_game.state = STATE_PAUSED
    main_game.score_system.score = 1234
    assert main_game.menu_lines() == _pause_lines("Score: 1,234", "M: Mute sound")
    main_game.sound.toggle_mute()
    assert main_game.menu_lines() == _pause_lines("Score: 1,234", "M: Unmute sound")


# Criterion 5
def test_no_dead_controls(main_game):
    """No SPACE or mouse line on pause; the start screen keeps its full list."""
    main_game.state = STATE_PAUSED
    texts = _texts(main_game)
    for word in ("space", "mouse", "click", "start"):
        assert not any(word in text.lower() for text in texts), word
    assert "ESC: Resume" in texts

    main_game.state = STATE_START
    start = {line[0]: line[3] for line in main_game.menu_lines()}
    assert start["SPACE: Start / Restart"] == MID + 80
    assert start["Mouse Click: Launch defense missile"] == MID + 50
    assert start["ESC: Pause / Resume"] == MID + 110
    assert start["Press SPACE to Start"] == MID + 190


def _press(game, key):
    """Post one KEYDOWN for ``key`` and run it through the real input path."""
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    game.handle_actions(game.input_system.handle_events())
    pygame.event.clear()


# Criterion 6
def test_listed_keys_work_while_paused(main_game):
    """M mutes without leaving pause; ESC resumes."""
    main_game.handle_actions(PAUSE)
    _press(main_game, pygame.K_m)
    assert main_game.sound.muted is True
    assert main_game.state == STATE_PAUSED
    assert "M: Unmute sound" in _texts(main_game)
    _press(main_game, pygame.K_ESCAPE)
    assert main_game.state == STATE_PLAYING


def _snapshot(game, missile, explosion):
    """Return every piece of state that pausing and drawing must leave alone."""
    return {
        "game_time": game.game_time,
        "score": game.score_system.score,
        "missile_pos": Vector2(missile.position),
        "trail": [tuple(p) for p in missile.trail],
        "radius": explosion.radius,
        "active": explosion.is_active,
        "cooldown": game.base.cooldown_time,
        "buildings": len(game.buildings),
        "shake": game.shake_intensity,
    }


# Criterion 7
def test_pausing_and_drawing_change_nothing(main_game):
    """Ten paused frames leave time, score, entities, cooldown and shake untouched."""
    missile = _park(main_game, *MISSILE)
    missile.trail.extend([Vector2(100, 190), Vector2(100, 196)])
    explosion = main_game.explosion_pool.get_explosion(300, 300, is_player=True)
    main_game.explosions.append(explosion)
    main_game.score_system.score = 77
    main_game.game_time = 12.5
    main_game.base.cooldown_time = 0.7
    before = _snapshot(main_game, missile, explosion)
    main_game.handle_actions(PAUSE)
    for _ in range(10):
        main_game.draw_start_screen()
    main_game.handle_actions(PAUSE)
    assert main_game.state == STATE_PLAYING
    assert _snapshot(main_game, missile, explosion) == before


# Criterion 8
def test_one_flip_per_frame(main_game, monkeypatch):
    """draw_scene never flips; draw and every menu screen flip exactly once."""
    flips = [0]

    def count():
        flips[0] += 1

    monkeypatch.setattr(pygame.display, "flip", count)

    def flips_for(call):
        flips[0] = 0
        call()
        return flips[0]

    assert flips_for(main_game.draw_scene) == 0
    assert flips_for(main_game.draw) == 1
    for state in (STATE_PAUSED, STATE_START, STATE_GAME_OVER):
        main_game.state = state
        assert flips_for(main_game.draw_start_screen) == 1, state


# Criterion 9
@pytest.mark.parametrize("state", [STATE_START, STATE_GAME_OVER])
def test_start_and_game_over_hide_scene(main_game, state):
    """The start and game over screens are a uniform background, no missile shows."""
    _park(main_game, *MISSILE)
    main_game.state = state
    main_game.draw_start_screen()
    assert _px(main_game, MISSILE) == _px(main_game, SKY)


def _fake_events(monkeypatch, game, script, on_call=None):
    """Make ``handle_events`` return ``script[i]`` on call ``i + 1``; the last entry must quit."""
    assert script[-1] == {"quit": True}
    calls = [0]

    def fake():
        calls[0] += 1
        if on_call:
            on_call(calls[0])
        return script[calls[0] - 1]

    monkeypatch.setattr(game, "handle_events", fake)
    return calls


# Criterion 10
def test_pause_through_real_loop(main_game, monkeypatch):
    """Play frames and pause frames both draw the scene; pause frames use the menu path."""
    clock = [1000.0]
    monkeypatch.setattr(utils.timer, "time", types.SimpleNamespace(time=lambda: clock[0]))
    main_game.timer.reset()
    script = [{}] * 5 + [PAUSE] + [{}] * 5 + [{"quit": True}]

    def tick(call):
        clock[0] += 1 / 60

    _fake_events(monkeypatch, main_game, script, on_call=tick)

    counts = {"scene": 0, "menu": 0}
    real_scene = main_game.draw_scene
    real_menu = main_game.draw_start_screen

    def scene_spy():
        counts["scene"] += 1
        return real_scene()

    def menu_spy():
        counts["menu"] += 1
        return real_menu()

    monkeypatch.setattr(main_game, "draw_scene", scene_spy)
    monkeypatch.setattr(main_game, "draw_start_screen", menu_spy)
    main_game.start_game_loop()
    assert counts == {"scene": 11, "menu": 6}
    assert main_game.state == STATE_PAUSED
