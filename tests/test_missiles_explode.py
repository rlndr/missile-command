"""Tests for job 002-missiles-explode.

Defense missiles fly in a straight line to the click point and detonate
there. Explosions grow and shrink on game time (``dt``), and only player
explosions destroy incoming missiles inside their current radius.
"""

import inspect
import random

import pygame
import pytest

import entities
import entities.base
import entities.terrain
from entities import DefenseMissile, IncomingMissile
from entities.terrain import ExplosionPool
from game.constants import (
    COLOR_YELLOW,
    DEFENSE_MISSILE_SPEED,
    DT_DEFAULT,
    EXPLOSION_EXPANSION_TIME,
    EXPLOSION_MAX_RADIUS,
    LAUNCHER_X,
    LAUNCHER_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)

Vector2 = pygame.math.Vector2
LAUNCHER = Vector2(LAUNCHER_X, LAUNCHER_Y)
TARGET = Vector2(400, 300)


def _stationary_incoming(x, y):
    """Return an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position = Vector2(x, y)
    missile.velocity = Vector2(0, 0)
    return missile


def _fire(game, target=(400, 300)):
    """Fire one defense missile through the game and return it."""
    game.base.cooldown_time = 0
    game.spawn_defense_missile(target)
    assert len(game.defense_missiles) == 1
    return game.defense_missiles[0]


def _perpendicular_distance(point, start, end):
    """Distance from ``point`` to the infinite line through ``start`` and ``end``."""
    line = end - start
    rel = point - start
    return abs(line.x * rel.y - line.y * rel.x) / line.length()


# --- Criteria 1-4: DefenseMissile flight -----------------------------------


def test_straight_flight():
    """Criterion 1: velocity is fixed, path is the launcher-target line, speed is exact."""
    m = DefenseMissile(Vector2(400, 300))
    initial_velocity = Vector2(m.velocity)
    step = DEFENSE_MISSILE_SPEED * DT_DEFAULT
    for n in range(1, 34):
        m.update(DT_DEFAULT)
        assert m.velocity == initial_velocity
        assert _perpendicular_distance(m.position, LAUNCHER, TARGET) < 1e-6
        assert (m.position - LAUNCHER).length() == pytest.approx(n * step, abs=1e-6)


def test_arrival_on_step_34_and_stays():
    """Criterion 2: arrival on the 34th update, snapped exactly, then no movement."""
    m = DefenseMissile(Vector2(400, 300))
    assert m.reached_target is False
    for _ in range(33):
        m.update(DT_DEFAULT)
    assert m.reached_target is False
    m.update(DT_DEFAULT)
    assert m.reached_target is True
    assert m.position == Vector2(400, 300)
    for _ in range(10):
        m.update(DT_DEFAULT)
        assert m.position == Vector2(400, 300)
        assert m.reached_target is True


@pytest.mark.parametrize("dt", [DT_DEFAULT, 0.16])
@pytest.mark.parametrize("target", [(780, 580), (20, 580), (780, 20), (400, 300)])
def test_no_overshoot_stays_on_screen(target, dt):
    """Criterion 3: never leaves the screen and ends exactly on the target."""
    target = Vector2(target)
    m = DefenseMissile(target)
    for _ in range(300):
        m.update(dt)
        assert 0 <= m.position.x <= SCREEN_WIDTH
        assert 0 <= m.position.y <= SCREEN_HEIGHT
        if m.reached_target:
            break
    assert m.reached_target is True
    assert m.position == target


def test_zero_length_shot():
    """Criterion 4: targeting the launcher itself is safe and arrives immediately."""
    m = DefenseMissile(Vector2(LAUNCHER_X, LAUNCHER_Y))
    m.update(DT_DEFAULT)
    assert m.reached_target is True
    assert m.position == LAUNCHER


# --- Criterion 5: detonation through the game ------------------------------


def test_detonation_through_game(main_game):
    """Criterion 5: one player explosion at the target on frame 34, missile removed next."""
    random.seed(0)
    game = main_game
    m = _fire(game)
    for _ in range(33):
        game.update(DT_DEFAULT)
    assert game.explosions == []
    assert m.is_destroyed is False

    game.update(DT_DEFAULT)
    assert m.is_destroyed is True
    assert len(game.explosions) == 1
    explosion = game.explosions[0]
    assert explosion.is_player is True
    assert explosion.position == Vector2(400, 300)

    game.update(DT_DEFAULT)
    assert game.defense_missiles == []


# --- Criteria 6-7: Explosion on dt -----------------------------------------


def test_explosion_timeline_on_dt():
    """Criterion 6: radius follows elapsed game time through grow, shrink and expiry."""
    e = ExplosionPool().get_explosion(100, 100)
    assert e.radius == 0
    assert e.elapsed == 0.0
    assert e.is_active is True
    e.update(0.0)
    assert e.is_active is True

    e.update(0.25)
    assert e.radius == pytest.approx(EXPLOSION_MAX_RADIUS * 0.5)
    e.update(0.25)
    assert e.radius == pytest.approx(EXPLOSION_MAX_RADIUS)
    e.update(0.15)
    assert e.radius == pytest.approx(EXPLOSION_MAX_RADIUS * 0.5)
    e.update(0.2)
    assert e.is_active is False
    assert e.radius == 0


def test_no_wall_clock(monkeypatch):
    """Criterion 7: nothing here reads pygame.time.get_ticks; lifetime counts frames."""

    def _boom():
        raise AssertionError("pygame.time.get_ticks must not be called")

    monkeypatch.setattr(pygame.time, "get_ticks", _boom)

    m = DefenseMissile(Vector2(400, 300))
    for _ in range(100):
        m.update(DT_DEFAULT)
        if m.reached_target:
            break
    assert m.reached_target is True

    pool = ExplosionPool()
    e = pool.get_explosion(100, 100)
    for _ in range(47):
        e.update(DT_DEFAULT)
    assert e.is_active is True
    for _ in range(2):
        e.update(DT_DEFAULT)
    assert e.is_active is False


def test_terrain_has_no_get_ticks():
    """Criterion 7 (scope): no pygame.time.get_ticks() anywhere in entities/terrain.py."""
    assert "get_ticks" not in inspect.getsource(entities.terrain)


# --- Criteria 8-12: explosions vs incoming missiles ------------------------


def test_kill_radius(main_game):
    """Criterion 8: incoming missiles within the current radius die, others survive."""
    random.seed(0)
    game = main_game
    e = game.explosion_pool.get_explosion(400, 300, is_player=True)
    game.explosions.append(e)
    e.update(0.25)
    assert e.radius == pytest.approx(40)

    inside = [_stationary_incoming(x, y) for x, y in [(400, 300), (430, 300), (400, 335), (370, 310)]]
    outside = [_stationary_incoming(x, y) for x, y in [(450, 300), (400, 360)]]
    game.incoming_missiles = inside + outside

    game.check_collisions()
    for missile in inside:
        assert missile.is_destroyed is True
    for missile in outside:
        assert missile.is_destroyed is False


def test_uses_current_radius_not_max(main_game):
    """Criterion 9: a missile outside the current radius survives until the blast grows."""
    random.seed(0)
    game = main_game
    e = game.explosion_pool.get_explosion(400, 300, is_player=True)
    game.explosions.append(e)
    e.update(0.25)
    missile = _stationary_incoming(460, 300)
    game.incoming_missiles = [missile]

    game.check_collisions()
    assert missile.is_destroyed is False

    e.update(0.2)
    assert e.radius == pytest.approx(EXPLOSION_MAX_RADIUS * 0.45 / EXPLOSION_EXPANSION_TIME)
    game.check_collisions()
    assert missile.is_destroyed is True


def test_non_player_explosions_do_not_intercept(main_game):
    """Criterion 10: building-hit style explosions leave incoming missiles alone."""
    random.seed(0)
    game = main_game
    e = game.explosion_pool.get_explosion(400, 300)
    assert e.is_player is False
    game.explosions.append(e)
    e.update(0.25)
    missile = _stationary_incoming(410, 300)
    game.incoming_missiles = [missile]

    game.check_collisions()
    assert missile.is_destroyed is False


def test_no_contact_detonation(main_game):
    """Criterion 11: flying through an incoming missile neither detonates nor kills it."""
    random.seed(0)
    game = main_game
    incoming = _stationary_incoming(400, 420)
    game.incoming_missiles = [incoming]
    # Sanity: (400, 420) is on the flight path and far from the target.
    assert _perpendicular_distance(Vector2(400, 420), LAUNCHER, TARGET) < 1.0
    assert (TARGET - Vector2(400, 420)).length() > EXPLOSION_MAX_RADIUS

    m = _fire(game)
    for _ in range(33):
        game.update(DT_DEFAULT)
        game.check_collisions()
        assert game.explosions == []
        assert m.is_destroyed is False
    game.update(DT_DEFAULT)
    game.check_collisions()
    assert incoming.is_destroyed is False


def test_end_to_end_intercept(main_game):
    """Criterion 12: firing next to an incoming missile kills it shortly after arrival.

    The spec's bound of frame 80 is not reachable with the criterion-6
    timeline: the explosion starts at radius 0 on frame 34 and grows by
    ``EXPLOSION_MAX_RADIUS / EXPLOSION_EXPANSION_TIME * DT_DEFAULT`` (~2.67 px)
    per frame, so it reaches the missile 20 px away on frame 41.
    """
    random.seed(0)
    game = main_game
    incoming = _stationary_incoming(420, 300)
    game.incoming_missiles = [incoming]

    _fire(game)
    killed_on = None
    for frame in range(1, 42):
        game.update(DT_DEFAULT)
        game.check_collisions()
        if incoming.is_destroyed:
            killed_on = frame
            break
    assert killed_on is not None
    assert 34 <= killed_on <= 41
    game.draw()


# --- Criteria 14-16 --------------------------------------------------------


def test_pool_reuse_resets_state():
    """Criterion 14: a reused pooled explosion carries nothing over from its last use."""
    pool = ExplosionPool(pool_size=1)
    first = pool.get_explosion(400, 300, is_player=True)
    assert first.is_player is True
    for _ in range(100):
        first.update(DT_DEFAULT)
        if not first.is_active:
            break
    assert first.is_active is False
    pool.return_explosion(first)

    reused = pool.get_explosion(10, 20)
    assert reused is first
    assert reused.is_player is False
    assert reused.radius == 0
    assert reused.elapsed == 0.0
    assert reused.is_active is True
    assert reused.position == Vector2(10, 20)


def test_single_explosion_class():
    """Criterion 15: one Explosion class, exported from entities via entities.terrain."""
    from entities import Explosion as from_package
    from entities.terrain import Explosion as from_terrain

    assert from_package is from_terrain
    assert "Explosion" not in vars(entities.base)


def test_missile_drawn_where_it_is(main_game):
    """Criterion 16: the yellow dot is drawn at the missile's current position."""
    random.seed(0)
    game = main_game
    m = _fire(game)
    for _ in range(17):
        game.update(DT_DEFAULT)
    game.draw()
    assert game.screen.get_at((int(m.position.x), int(m.position.y)))[:3] == COLOR_YELLOW
