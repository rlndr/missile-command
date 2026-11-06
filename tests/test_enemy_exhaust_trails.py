"""Tests for job 010-enemy-exhaust-trails: fading exhaust trails behind enemy missiles."""

import inspect
import random

import pygame
import pytest

import entities.base
import entities.missile
import game.constants as constants
from entities import DefenseMissile, IncomingMissile
from game.constants import (COLOR_BLACK, COLOR_GRAY, COLOR_ORANGE, COLOR_RED,
                            COLOR_YELLOW, DT_DEFAULT, INCOMING_MISSILE_SPEED,
                            SCREEN_HEIGHT, SCREEN_WIDTH, STATE_GAME_OVER,
                            STATE_PAUSED, STATE_PLAYING)

Vector2 = pygame.math.Vector2


def _controlled_missile(y=100):
    """Return an incoming missile at ``(400, y)`` flying straight down at 200 px/s, trail empty."""
    m = IncomingMissile(Vector2(400, 500))
    m.position = Vector2(400, y)
    m.velocity = Vector2(0, INCOMING_MISSILE_SPEED)
    m.trail.clear()
    return m


def _run(m, dt, steps):
    """Call ``m.update(dt)`` ``steps`` times."""
    for _ in range(steps):
        m.update(dt)


def _ys(m):
    """Return the y of every trail sample, oldest first."""
    return [p.y for p in m.trail]


def _px(surface, x, y):
    """Return the RGB of the pixel at ``(x, y)``."""
    return tuple(surface.get_at((x, y)))[:3]


def _surface_draw(m):
    """Draw ``m``'s trail on a fresh black screen-sized surface and return the surface."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(COLOR_BLACK)
    m.draw_trail(surface)
    return surface


def _sky(game, y):
    """Return the background colour at row ``y`` (x = 300 is otherwise empty in these tests)."""
    return _px(game.screen, 300, y)


def _sixty_frame_game(game):
    """Put one controlled missile in ``game``, run 60 frames and return the missile."""
    m = _controlled_missile()
    game.incoming_missiles = [m]
    for _ in range(60):
        game.update(DT_DEFAULT)
        game.check_collisions()
    return m


def _six_step_missile():
    """Return a controlled missile after six ``update(0.05)`` calls (head at y = 160)."""
    m = _controlled_missile()
    _run(m, 0.05, 6)
    return m


def _is_colour(colour):
    """Return True if ``colour`` is a 3-tuple of ints in 0-255."""
    return (isinstance(colour, tuple) and len(colour) == 3
            and all(type(c) is int and 0 <= c <= 255 for c in colour))


# Criterion 1
def test_constants():
    """Trail size constants are positive ints and its colours are orange and grey."""
    assert constants.ENEMY_TRAIL_SPACING == 6
    assert constants.ENEMY_TRAIL_MAX_POINTS == 12
    assert constants.ENEMY_TRAIL_WIDTH == 2
    for value in (constants.ENEMY_TRAIL_SPACING, constants.ENEMY_TRAIL_MAX_POINTS,
                  constants.ENEMY_TRAIL_WIDTH):
        assert type(value) is int and value > 0
    head, tail = constants.ENEMY_TRAIL_HEAD_COLOR, constants.ENEMY_TRAIL_TAIL_COLOR
    assert head == COLOR_ORANGE
    assert tail == COLOR_GRAY
    assert _is_colour(head) and _is_colour(tail)
    assert head != tail
    assert COLOR_RED not in (head, tail)


# Criterion 2
def test_empty_at_birth():
    """A new missile has no trail, no segments and draws nothing."""
    m = IncomingMissile(Vector2(400, 500))
    assert len(m.trail) == 0
    assert m.trail_segments() == []
    surface = _surface_draw(m)
    assert pygame.mask.from_threshold(surface, COLOR_BLACK, (1, 1, 1, 255)).count() \
        == SCREEN_WIDTH * SCREEN_HEIGHT


# Criterion 3
def test_sampling_records_copies_before_moving():
    """Each 10 px step records the pre-move position as a separate Vector2."""
    m = _six_step_missile()
    assert len(m.trail) == 6
    assert _ys(m) == pytest.approx([100, 110, 120, 130, 140, 150])
    assert [p.x for p in m.trail] == pytest.approx([400] * 6)
    assert tuple(m.position) == pytest.approx((400, 160))
    assert all(p is not m.position for p in m.trail)
    assert len({id(p) for p in m.trail}) == 6


# Criterion 4
def test_spacing():
    """At 2 px per step a sample is only added once the missile is 6 px past the last one."""
    m = _controlled_missile()
    _run(m, 0.01, 10)
    assert _ys(m) == pytest.approx([100, 106, 112, 118])
    assert m.position.y == pytest.approx(120)


# Criterion 5
def test_cap():
    """The trail never keeps more than ENEMY_TRAIL_MAX_POINTS samples; the oldest go first."""
    m = _controlled_missile()
    for _ in range(20):
        m.update(0.05)
        assert len(m.trail) <= constants.ENEMY_TRAIL_MAX_POINTS
    assert len(m.trail) == 12
    assert m.trail[0].y == pytest.approx(180)
    assert m.trail[-1].y == pytest.approx(290)
    assert m.position.y == pytest.approx(300)


# Criterion 6
@pytest.mark.parametrize("dt", [1 / 30, DT_DEFAULT, 1 / 144])
def test_length_independent_of_frame_rate(dt):
    """Two seconds of flight leaves a full trail 72-90 px long at 30, 60 or 144 fps."""
    m = _controlled_missile(y=0)
    _run(m, dt, round(2.0 / dt))
    assert len(m.trail) == 12
    assert 72 <= m.position.distance_to(m.trail[0]) <= 90


# Criterion 7
def test_destroyed_missile_stops_recording():
    """After destroy() neither the trail nor the head changes."""
    m = _controlled_missile()
    _run(m, 0.05, 3)
    before = [tuple(p) for p in m.trail]
    head = tuple(m.position)
    m.destroy()
    _run(m, 0.05, 5)
    assert [tuple(p) for p in m.trail] == before
    assert len(before) == 3
    assert tuple(m.position) == head


# Criterion 8
def test_segments():
    """Segments chain from the head to the oldest sample and blend head to tail colour."""
    m = _six_step_missile()
    segments = m.trail_segments()
    assert len(segments) == 6
    assert tuple(segments[0][0]) == pytest.approx((400, 160))
    assert tuple(segments[0][1]) == pytest.approx((400, 150))
    for prev, seg in zip(segments, segments[1:]):
        assert tuple(seg[0]) == pytest.approx(tuple(prev[1]))
    assert tuple(segments[-1][1]) == pytest.approx((400, 100))

    head, tail = constants.ENEMY_TRAIL_HEAD_COLOR, constants.ENEMY_TRAIL_TAIL_COLOR
    colours = [seg[2] for seg in segments]
    assert colours[0] == head
    assert colours[5] == tail
    assert all(_is_colour(c) for c in colours)
    for ch in range(3):
        lo, hi = sorted((head[ch], tail[ch]))
        values = [c[ch] for c in colours]
        assert all(lo <= v <= hi for v in values)
        steps = [b - a for a, b in zip(values, values[1:])]
        if tail[ch] >= head[ch]:
            assert all(s >= 0 for s in steps)
        else:
            assert all(s <= 0 for s in steps)

    single = _controlled_missile()
    single.update(0.05)
    assert len(single.trail) == 1
    only = single.trail_segments()
    assert len(only) == 1
    assert only[0][2] == head


# Criterion 9
def test_pixels():
    """draw_trail draws a thin line from head to tail, newest colour on top, and no head."""
    m = _six_step_missile()
    surface = _surface_draw(m)
    assert _px(surface, 400, 155) == constants.ENEMY_TRAIL_HEAD_COLOR
    assert _px(surface, 400, 105) == constants.ENEMY_TRAIL_TAIL_COLOR
    assert _px(surface, 400, 145) == m.trail_segments()[1][2]
    assert _px(surface, 400, 95) == COLOR_BLACK
    assert _px(surface, 400, 165) == COLOR_BLACK
    assert _px(surface, 397, 130) == COLOR_BLACK
    assert _px(surface, 403, 130) == COLOR_BLACK
    box = pygame.Rect(390, 90, 21, 80)
    for y in range(box.top, box.bottom):
        for x in range(box.left, box.right):
            assert _px(surface, x, y) != COLOR_RED


# Criterion 10
def test_wired_into_game_frame(main_game):
    """MainGame.draw() draws the trail behind the red head."""
    game = main_game
    m = _sixty_frame_game(game)
    assert tuple(m.position) == pytest.approx((400, 300))
    assert len(m.trail) == 12
    game.draw()
    assert _px(game.screen, 400, 300) == COLOR_RED
    assert _px(game.screen, 400, 290) == m.trail_segments()[1][2]
    mid = _px(game.screen, 400, 250)
    assert mid != COLOR_RED
    assert mid != _sky(game, 250)
    assert _px(game.screen, 400, 210) == _sky(game, 210)


# Criterion 11
def test_draw_order(main_game):
    """Trails are drawn before defense missiles and enemy heads."""
    game = main_game
    _sixty_frame_game(game)
    defense = DefenseMissile(Vector2(400, 300))
    defense.position = Vector2(400, 250)
    game.defense_missiles.append(defense)
    other = IncomingMissile(Vector2(400, 500))
    other.position = Vector2(400, 232)
    other.velocity = Vector2(0, 0)
    other.trail.clear()
    game.incoming_missiles.append(other)
    game.draw()
    assert _px(game.screen, 400, 250) == COLOR_YELLOW
    assert _px(game.screen, 400, 232) == COLOR_RED


# Criterion 12
def test_destroyed_missile_draws_no_trail(main_game):
    """A destroyed missile's trail is not drawn."""
    game = main_game
    m = _sixty_frame_game(game)
    m.destroy()
    game.draw()
    assert _px(game.screen, 400, 250) == _sky(game, 250)
    assert _px(game.screen, 400, 290) == _sky(game, 290)


# Criterion 13
def test_pause_freezes_and_restart_clears(main_game):
    """Pausing and the menu screen leave the trail alone; a restart drops all missiles."""
    game = main_game
    m = _controlled_missile()
    game.incoming_missiles = [m]
    _run(game, 0.05, 4)
    saved = [tuple(p) for p in m.trail]
    assert len(saved) == 4

    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    game.draw_start_screen()
    assert [tuple(p) for p in m.trail] == saved
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING
    assert [tuple(p) for p in m.trail] == saved

    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER
    game.handle_actions({"start": True})
    assert game.incoming_missiles == []


# Criterion 14
def test_real_spawns(main_game):
    """Randomly spawned missiles build bounded trails that stay near the screen."""
    game = main_game
    random.seed(1)
    for _ in range(3):
        game.spawn_incoming_missile()
    for _ in range(90):
        game.update(DT_DEFAULT)
        game.check_collisions()
    game.draw()
    area = pygame.Rect(0, -60, SCREEN_WIDTH, SCREEN_HEIGHT + 120)
    assert game.incoming_missiles
    for m in game.incoming_missiles:
        assert 1 <= len(m.trail) <= constants.ENEMY_TRAIL_MAX_POINTS
        for p in m.trail:
            assert area.collidepoint(p.x, p.y)


# Criterion 15
def test_scope_fence():
    """Defense missiles and the launcher are untouched; trails use dt, not wall time."""
    assert "trail" not in inspect.getsource(entities.missile.DefenseMissile)
    assert "ENEMY_TRAIL" not in inspect.getsource(entities.base)
    assert "get_ticks" not in inspect.getsource(entities.missile)
