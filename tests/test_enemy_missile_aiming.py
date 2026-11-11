"""Tests for job 003-enemy-missile-aiming-and.

Enemy missiles aim at a random point across a standing building, fly
straight through it with no hidden offset, and a missile that reaches the
ground without hitting anything bursts there in a small, harmless blast.
"""

import random

import pygame
import pytest

import game.constants as constants
from entities import IncomingMissile
from entities.terrain import ExplosionPool
from game.constants import (
    BUILDING_EXPLOSION_MAX_RADIUS,
    DT_DEFAULT,
    EXPLOSION_MAX_RADIUS,
    GROUND_IMPACT_EXPANSION_TIME,
    GROUND_IMPACT_MAX_RADIUS,
    GROUND_IMPACT_SHRINK_TIME,
    GROUND_Y,
    INCOMING_MISSILE_SPEED,
    MISSILE_INTERCEPT_POINTS,
    SCREEN_WIDTH,
    STATE_PAUSED,
)

Vector2 = pygame.math.Vector2


@pytest.fixture
def game(main_game):
    """The shared ``main_game`` fixture with ``random`` seeded to 0."""
    random.seed(0)
    return main_game


@pytest.fixture
def spy(game, monkeypatch):
    """``game`` with ``sound.play`` replaced by a recorder; yields ``(game, calls)``."""
    calls = []
    monkeypatch.setattr(game.sound, "play", lambda name: calls.append(name) or True)
    return game, calls


def _park_missile(game, x, y):
    """Add a stationary ``IncomingMissile`` at ``(x, y)`` to ``game`` and return it."""
    missile = IncomingMissile(Vector2(x, y))
    missile.position = Vector2(x, y)
    missile.velocity = Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def _ground_explosions(game):
    """Return the ground explosions in ``game.explosions``."""
    return [e for e in game.explosions if e.is_ground]


def _healths(game):
    """Return every building's current health, in order."""
    return [b.health_current for b in game.buildings]


# --- Criteria 1-3: aim ------------------------------------------------------


def _inside(building, point):
    """True when ``point`` lies in ``building``'s rect, from its roof down to ``GROUND_Y``."""
    return (building.position.x <= point.x <= building.position.x + building.width
            and building.position.y <= point.y <= GROUND_Y)


def test_aim_spreads_across_standing_buildings(game):
    """Criterion 1: every target is inside a standing building, not just on its left edge."""
    assert len(game.buildings) == 8
    for _ in range(200):
        game.spawn_incoming_missile()
    assert len(game.incoming_missiles) == 200
    off_edge = False
    for m in game.incoming_missiles:
        hits = [b for b in game.buildings if _inside(b, m.target)]
        assert hits, m.target
        if any(m.target.x > b.position.x + 5 for b in hits):
            off_edge = True
    assert off_edge


def test_aim_only_last_standing_building(game):
    """Criterion 2: with 7 buildings down, every target is inside the last one."""
    for building in game.buildings[:7]:
        building.is_destroyed = True
    for _ in range(20):
        game.spawn_incoming_missile()
    for m in game.incoming_missiles:
        assert 710 <= m.target.x <= 770
        assert 540 <= m.target.y <= GROUND_Y
    assert len({m.target.x for m in game.incoming_missiles}) > 1


def test_fallback_target_on_ground(game):
    """Criterion 3: with no building standing, targets lie on the ground line."""
    for building in game.buildings:
        building.is_destroyed = True
    for _ in range(20):
        game.spawn_incoming_missile()
    assert len(game.incoming_missiles) == 20
    for m in game.incoming_missiles:
        assert m.target.y == GROUND_Y
        assert 100 <= m.target.x <= SCREEN_WIDTH - 100


# --- Criteria 4-5: flight line ----------------------------------------------


def test_target_has_no_offset():
    """Criterion 4: the target is exactly the given point and velocity heads straight at it."""
    random.seed(1)
    m = IncomingMissile(Vector2(300, 500))
    assert m.target == Vector2(300, 500)
    assert m.velocity.length() == pytest.approx(INCOMING_MISSILE_SPEED)
    to_target = m.target - m.position
    assert m.velocity.cross(to_target) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("target", [(300, 500), (60, 560), (740, 579), (400, GROUND_Y)])
def test_missile_flies_through_target(target):
    """Criterion 5: when the missile reaches the target's y, its x is on the target."""
    random.seed(2)
    for _ in range(10):
        m = IncomingMissile(Vector2(target))
        while m.position.y < m.target.y:
            m.update(DT_DEFAULT)
        assert abs(m.position.x - m.target.x) <= 4


# --- Criteria 6-11: ground impacts ------------------------------------------


def test_ground_impact_on_ground_line(game):
    """Criterion 6: a missile on the ground line bursts in one small ground blast."""
    missile = _park_missile(game, 400, GROUND_Y)
    game.check_collisions()
    assert missile.is_destroyed
    assert len(game.explosions) == 1
    exp = game.explosions[0]
    assert exp.is_ground is True
    assert exp.is_player is False
    assert exp.is_building is False
    assert exp.position == Vector2(400, GROUND_Y)
    assert exp.max_radius == GROUND_IMPACT_MAX_RADIUS
    assert GROUND_IMPACT_MAX_RADIUS < EXPLOSION_MAX_RADIUS


def test_ground_impact_below_ground(game):
    """Criterion 7: a missile past the ground line bursts on the ground line."""
    missile = _park_missile(game, 400, GROUND_Y + 10)
    game.check_collisions()
    assert missile.is_destroyed
    assert len(game.explosions) == 1
    assert game.explosions[0].is_ground is True
    assert game.explosions[0].position == Vector2(400, GROUND_Y)


def test_no_ground_impact_above_ground(game):
    """Criterion 8: a missile one pixel above the ground is left alone."""
    missile = _park_missile(game, 400, GROUND_Y - 1)
    game.check_collisions()
    assert not missile.is_destroyed
    assert game.explosions == []


def test_building_hit_beats_ground_impact(game):
    """Criterion 9: a missile in a building at ground level hits the building."""
    building = game.buildings[0]
    assert building.health_current == 100
    missile = _park_missile(game, 60, GROUND_Y)
    game.check_collisions()
    assert missile.is_destroyed
    assert building.health_current == 66
    assert _ground_explosions(game) == []


def test_intercept_beats_ground_impact(game):
    """Criterion 10: a missile on the ground inside a player blast is intercepted."""
    blast = game.explosion_pool.get_explosion(400, GROUND_Y, is_player=True)
    blast.radius = 20
    game.explosions.append(blast)
    score_before = game.score_system.score
    missile = _park_missile(game, 400, GROUND_Y)
    game.check_collisions()
    assert missile.is_destroyed
    assert game.score_system.score == score_before + MISSILE_INTERCEPT_POINTS
    assert _ground_explosions(game) == []


def test_ground_blast_is_harmless(game):
    """Criterion 11: a ground blast at full size neither intercepts, scores nor damages."""
    _park_missile(game, 400, GROUND_Y)
    game.check_collisions()
    blast = _ground_explosions(game)[0]
    while blast.elapsed < GROUND_IMPACT_EXPANSION_TIME - 1e-9:
        game.update(DT_DEFAULT)
    assert blast.radius == pytest.approx(GROUND_IMPACT_MAX_RADIUS, rel=0.1)

    score_before = game.score_system.score
    healths_before = _healths(game)
    second = _park_missile(game, 400 + 10, GROUND_Y - 5)
    assert blast.position.distance_to(second.position) <= blast.radius
    game.check_collisions()
    assert not second.is_destroyed
    assert game.score_system.score == score_before
    assert _healths(game) == healths_before


# --- Criterion 12: sound ----------------------------------------------------


def test_ground_impacts_play_one_impact(spy):
    """Criterion 12: two ground impacts in one call play ``"impact"`` once."""
    game, calls = spy
    _park_missile(game, 380, GROUND_Y)
    _park_missile(game, 420, GROUND_Y)
    game.check_collisions()
    assert calls == ["impact"]
    assert len(_ground_explosions(game)) == 2
    game.check_collisions()
    assert calls == ["impact"]


def test_ground_and_building_hit_play_one_impact(spy):
    """Criterion 12: a ground impact and a building hit together play ``"impact"`` once."""
    game, calls = spy
    _park_missile(game, 400, GROUND_Y)
    _park_missile(game, 60, 560)
    game.check_collisions()
    assert calls == ["impact"]
    assert len(_ground_explosions(game)) == 1
    assert game.buildings[0].health_current == 66
    game.check_collisions()
    assert calls == ["impact"]


# --- Criterion 13: lifetime and pause ---------------------------------------


def test_ground_blast_expires(game):
    """Criterion 13: a ground blast is gone just after its expand and shrink time."""
    _park_missile(game, 400, GROUND_Y)
    game.check_collisions()
    total = 0.0
    while total <= GROUND_IMPACT_EXPANSION_TIME + GROUND_IMPACT_SHRINK_TIME:
        game.update(DT_DEFAULT)
        total += DT_DEFAULT
    assert not any(e.is_ground and e.is_active for e in game.explosions)


def test_ground_blast_freezes_while_paused(game, monkeypatch):
    """Criterion 13: the paused game loop doesn't age a ground blast."""
    _park_missile(game, 400, GROUND_Y)
    game.check_collisions()
    for _ in range(5):
        game.update(DT_DEFAULT)
    blast = _ground_explosions(game)[0]
    elapsed, radius = blast.elapsed, blast.radius
    assert radius > 0

    game.state = STATE_PAUSED
    calls = [0]

    def fake_handle_events():
        calls[0] += 1
        return {"quit": True} if calls[0] >= 10 else {}

    monkeypatch.setattr(game, "handle_events", fake_handle_events)
    game.start_game_loop()
    assert calls[0] == 10
    assert game.state == STATE_PAUSED
    assert blast.elapsed == elapsed
    assert blast.radius == radius


# --- Criterion 14: pool reuse -----------------------------------------------


def test_pool_reuse_clears_ground_settings():
    """Criterion 14: a reused ground explosion comes back as a default one."""
    pool = ExplosionPool(pool_size=1)
    ground = pool.get_explosion(400, GROUND_Y, is_ground=True)
    assert ground.is_ground is True
    assert ground.max_radius == GROUND_IMPACT_MAX_RADIUS
    pool.return_explosion(ground)
    exp = pool.get_explosion(100, 100)
    assert exp is ground
    assert exp.is_ground is False
    assert exp.max_radius == EXPLOSION_MAX_RADIUS


def test_pool_reuse_building_as_ground():
    """Criterion 14: a reused building explosion comes back as a ground one."""
    pool = ExplosionPool(pool_size=1)
    building = pool.get_explosion(100, 100, is_building=True)
    assert building.max_radius == BUILDING_EXPLOSION_MAX_RADIUS
    pool.return_explosion(building)
    exp = pool.get_explosion(400, GROUND_Y, is_ground=True)
    assert exp is building
    assert exp.is_building is False
    assert exp.is_ground is True
    assert exp.max_radius == GROUND_IMPACT_MAX_RADIUS
    assert exp.expansion_time == GROUND_IMPACT_EXPANSION_TIME
    assert exp.shrink_time == GROUND_IMPACT_SHRINK_TIME


# --- Criterion 15: constants ------------------------------------------------


@pytest.mark.parametrize("name", ["GROUND_IMPACT_MAX_RADIUS",
                                  "GROUND_IMPACT_EXPANSION_TIME",
                                  "GROUND_IMPACT_SHRINK_TIME"])
def test_ground_impact_constants(name):
    """Criterion 15: the ground impact constants are positive numbers."""
    value = getattr(constants, name)
    assert isinstance(value, (int, float))
    assert value > 0
