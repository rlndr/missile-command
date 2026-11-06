"""Tests for job 008-cooldown-indicator: a reload bar under the launcher."""

import gc

import pygame
import pytest

import game.constants as constants
import systems.score
from entities import DefensiveBase
from game.constants import (BASE_COOLDOWN_TIME, COLOR_BLACK, COLOR_WHITE,
                            DT_DEFAULT, SCREEN_HEIGHT, SCREEN_WIDTH,
                            STATE_GAME_OVER, STATE_PAUSED, STATE_PLAYING,
                            STATE_START)
from systems.game_loop import MainGame

FIRE = {"fire_missile": (400, 300)}
START = {"start": True}
PAUSE = {"toggle_pause": True}
TRACK = pygame.Rect(370, 584, 60, 4)
ROW = 585


def _bar_colours():
    """Return ``(track, fill, ready)`` colours, looked up lazily so a missing constant fails per test."""
    return (constants.COOLDOWN_BAR_TRACK_COLOR,
            constants.COOLDOWN_BAR_FILL_COLOR,
            constants.COOLDOWN_BAR_READY_COLOR)


def _px(surface, x, y):
    """Return the RGB of the pixel at ``(x, y)``."""
    return tuple(surface.get_at((x, y)))[:3]


def _region(surface, rect):
    """Return the RGB of every pixel in ``rect``."""
    return [_px(surface, x, y)
            for y in range(rect.top, rect.bottom) for x in range(rect.left, rect.right)]


def _surface_draw(base):
    """Draw ``base`` on a fresh black screen-sized surface and return the surface."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(COLOR_BLACK)
    base.draw_base(surface)
    return surface


def _fill_width(base):
    """Return the width of the base's fill rect."""
    return base.cooldown_bar_rects()[1].width


@pytest.fixture
def start_screen_game(monkeypatch, tmp_path):
    """Yield a ``MainGame()`` left in ``STATE_START``, with ``CONFIG_PATH`` patched first."""
    gc.collect()
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    game = MainGame()
    assert game.state == STATE_START
    yield game
    del game
    gc.collect()
    pygame.quit()


# Criterion 1
def test_constants():
    """Bar size constants are ints and its colours are distinct named RGB tuples."""
    assert constants.COOLDOWN_BAR_HEIGHT == 4
    assert constants.COOLDOWN_BAR_GAP == 4
    assert type(constants.COOLDOWN_BAR_HEIGHT) is int
    assert type(constants.COOLDOWN_BAR_GAP) is int
    colours = _bar_colours()
    for colour in colours:
        assert isinstance(colour, tuple) and len(colour) == 3
        assert all(type(c) is int and 0 <= c <= 255 for c in colour)
    assert len(set(colours)) == 3
    assert colours == (constants.COLOR_DARK_BLUE, constants.COLOR_ORANGE,
                       constants.COLOR_YELLOW)


# Criterion 2
def test_bar_position():
    """The track sits just under the launcher, on screen, the launcher's width."""
    base = DefensiveBase()
    track, fill = base.cooldown_bar_rects()
    bounds = base.get_bounds()
    assert track == pygame.Rect(370, 584, 60, 4)
    assert not track.colliderect(bounds)
    assert pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).contains(track)
    assert (track.left, track.width) == (bounds.left, bounds.width)
    assert (fill.left, fill.top, fill.height) == (track.left, track.top, track.height)


# Criterion 3
def test_reload_progress_values():
    """reload_progress() follows cooldown_time directly, not the stale cooldown_ratio."""
    base = DefensiveBase()
    assert base.cooldown_time == BASE_COOLDOWN_TIME
    assert base.reload_progress() == 0.0
    base.reset()
    assert base.reload_progress() == 1.0
    base.start_cooldown()
    assert base.reload_progress() == 0.0
    base.update(0.375)
    assert base.reload_progress() == pytest.approx(0.25)
    base.update(0.375)
    assert base.reload_progress() == pytest.approx(0.5)

    offline = DefensiveBase()
    offline.is_active = False
    offline.cooldown_time = 0.0
    assert offline.reload_progress() == 0.0


# Criterion 4
@pytest.mark.parametrize("cooldown_time", [-1.0, 0.0, 0.001, 0.75, BASE_COOLDOWN_TIME,
                                           BASE_COOLDOWN_TIME * 2])
def test_progress_clamped_and_full_only_when_ready(cooldown_time):
    """Progress stays in [0, 1], and both it and the fill are full exactly when can_fire()."""
    base = DefensiveBase()
    base.cooldown_time = cooldown_time
    progress = base.reload_progress()
    assert 0.0 <= progress <= 1.0
    assert (progress == 1.0) == base.can_fire()
    track, fill = base.cooldown_bar_rects()
    assert (fill.width == track.width) == base.can_fire()
    if cooldown_time == 0.001:
        assert fill.width == 59


# Criterion 5
def test_fill_widths():
    """Fill width tracks the reload, rounded down."""
    base = DefensiveBase()
    base.reset()
    assert _fill_width(base) == 60
    base.start_cooldown()
    assert _fill_width(base) == 0
    base.update(0.375)
    assert _fill_width(base) == 15
    base.update(0.375)
    assert _fill_width(base) == 30
    base.update(BASE_COOLDOWN_TIME)
    assert _fill_width(base) == 60


# Criterion 6
def test_pixels_ready():
    """A ready launcher draws a full yellow bar that stays inside the track."""
    _, _, ready = _bar_colours()
    base = DefensiveBase()
    base.reset()
    surface = _surface_draw(base)
    for x in (370, 399, 429):
        assert _px(surface, x, ROW) == ready
    assert _px(surface, 369, ROW) == COLOR_BLACK
    assert _px(surface, 430, ROW) == COLOR_BLACK
    assert _px(surface, 400, 582) == COLOR_BLACK
    assert _px(surface, 400, 555) == COLOR_WHITE


# Criterion 7
def test_pixels_just_fired():
    """Right after firing the bar is an empty track."""
    track_c, fill_c, ready_c = _bar_colours()
    base = DefensiveBase()
    base.reset()
    base.start_cooldown()
    pixels = _region(_surface_draw(base), TRACK)
    assert all(p == track_c for p in pixels)
    assert fill_c not in pixels and ready_c not in pixels


# Criterion 8
def test_pixels_half_reloaded():
    """Half way through the reload the left half is orange and the right half track."""
    track_c, fill_c, ready_c = _bar_colours()
    base = DefensiveBase()
    base.reset()
    base.start_cooldown()
    base.update(0.75)
    surface = _surface_draw(base)
    for x in (370, 385, 399):
        assert _px(surface, x, ROW) == fill_c
    for x in (400, 415, 429):
        assert _px(surface, x, ROW) == track_c
    assert ready_c not in _region(surface, TRACK)


# Criterion 9
def test_fills_over_real_reload(main_game):
    """Over a real reload the fill never shrinks and is full exactly when a click would fire."""
    game = main_game
    game.handle_actions(FIRE)
    assert not game.base.can_fire()
    previous = _fill_width(game.base)
    widths = {}
    for frame in range(1, 101):
        game.update(DT_DEFAULT)
        game.check_collisions()
        width = _fill_width(game.base)
        assert width >= previous
        assert (width == 60) == game.base.can_fire()
        widths[frame] = width
        previous = width
    assert widths[89] < 60
    assert widths[91] == 60


# Criterion 10
def test_wired_into_game_frame(main_game):
    """MainGame.draw() shows the bar mid-reload and when ready."""
    track_c, fill_c, ready_c = _bar_colours()
    game = main_game
    game.handle_actions(FIRE)
    game.update(0.75)
    game.draw()
    assert _px(game.screen, 375, ROW) == fill_c
    assert _px(game.screen, 415, ROW) == track_c
    game.update(1.0)
    game.draw()
    assert _px(game.screen, 375, ROW) == ready_c
    assert _px(game.screen, 415, ROW) == ready_c


# Criterion 11
def test_pause_freezes_bar(main_game):
    """Pausing and resuming leaves the bar where it was."""
    game = main_game
    game.handle_actions(FIRE)
    game.update(0.75)
    assert _fill_width(game.base) == 30
    game.handle_actions(PAUSE)
    game.handle_actions(PAUSE)
    assert game.state == STATE_PLAYING
    assert _fill_width(game.base) == 30
    assert not game.base.can_fire()


# Criterion 12
def test_new_game_shows_full_bar(start_screen_game):
    """Restarting after game over brings back a full, yellow bar."""
    _, _, ready_c = _bar_colours()
    game = start_screen_game
    game.handle_actions(START)
    game.handle_actions(FIRE)
    game.update(0.3)
    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER
    assert _fill_width(game.base) < 60
    game.handle_actions(START)
    assert _fill_width(game.base) == 60
    game.draw()
    assert _px(game.screen, 375, ROW) == ready_c


# Criterion 13
def test_not_on_menu_screens(start_screen_game):
    """The start and pause screens don't draw the bar."""
    colours = _bar_colours()
    game = start_screen_game
    game.draw_start_screen()
    assert _px(game.screen, 375, ROW) not in colours
    game.state = STATE_PAUSED
    game.draw_start_screen()
    assert _px(game.screen, 375, ROW) not in colours
