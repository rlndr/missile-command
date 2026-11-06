"""Tests for job 011-collision-score-tests: collision boundaries and score calculation.

Pins the current behaviour of the geometry helpers in ``utils/vector_math.py``,
every ``CollisionSystem`` check except ``building_in_explosion``, the hit-box
and blast-radius edges of ``MainGame.check_collisions()`` and the
``ScoreSystem`` arithmetic. Boundary points sit exactly on an edge or 0.5 px
(0.1 / 0.01 for radii) past it, so float error can't flip a result.
"""

import random
import types

import pygame
import pytest

import systems.score
from entities import Building, IncomingMissile
from entities.terrain import Explosion
from game.constants import (BUILDING_TYPES, EXPLOSION_EXPANSION_TIME, EXPLOSION_SHRINK_TIME,
                            MISSILE_INTERCEPT_POINTS)
from systems.collision import CollisionSystem
from systems.score import ScoreSystem
from utils.vector_math import check_circle_collision, get_distance

Vector2 = pygame.math.Vector2


def _stub(**attrs):
    """Return a ``SimpleNamespace`` with ``attrs``; a ``(x, y)`` ``position`` becomes a Vector2."""
    if "position" in attrs:
        attrs["position"] = Vector2(attrs["position"])
    return types.SimpleNamespace(**attrs)


def _building_b():
    """Return Building B: residential at (100, 500), bounds x 100..160 and y 500..540."""
    return Building(100, 500)


def _park(game, x, y):
    """Add an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity; return it."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position, missile.velocity = Vector2(x, y), Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def _player_blast(game, x, y, dt):
    """Add a pooled player explosion at ``(x, y)`` advanced by ``dt`` seconds; return it."""
    explosion = game.explosion_pool.get_explosion(x, y, is_player=True)
    explosion.update(dt)
    game.explosions.append(explosion)
    return explosion


@pytest.fixture
def game(main_game):
    """The shared ``main_game`` fixture with ``random`` seeded and an empty field."""
    random.seed(0)
    main_game.buildings = []
    main_game.incoming_missiles = []
    main_game.explosions = []
    return main_game


@pytest.fixture
def scores(monkeypatch, tmp_path):
    """A fresh ``ScoreSystem()`` built after ``CONFIG_PATH`` points under ``tmp_path``."""
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    return ScoreSystem()


# --- Geometry helpers -------------------------------------------------------

def test_get_distance_accepts_tuples_and_vectors_and_is_symmetric():
    """``get_distance`` is Euclidean, symmetric, takes tuples or Vector2, and is 0 on itself."""
    assert get_distance((0, 0), (3, 4)) == 5.0
    assert get_distance(Vector2(3, 4), (0, 0)) == 5.0
    assert get_distance((7, 7), (7, 7)) == 0.0


@pytest.mark.parametrize("point, expected", [
    ((13, 0), True),       # touching
    ((5, 12), True),       # distance exactly 13
    ((13.01, 0), False),
])
def test_check_circle_collision_is_inclusive(point, expected):
    """Circles of radius 8 and 5 collide when their centres are <= 13 apart."""
    assert check_circle_collision((0, 0), 8, point, 5) is expected


def test_check_circle_collision_zero_radii_same_point():
    """Two zero-radius circles on the same point collide."""
    assert check_circle_collision((1, 1), 0, (1, 1), 0) is True


# --- CollisionSystem --------------------------------------------------------

@pytest.mark.parametrize("point, expected", [
    ((213, 200), True),
    ((200, 187), True),
    ((213.5, 200), False),
])
def test_missile_to_missile_uses_radii_8_and_5(point, expected):
    """The incoming/defense check is a circle test with fixed radii 8 + 5."""
    incoming = _stub(position=(200, 200))
    defense = _stub(position=point)
    assert CollisionSystem.missile_to_missile_collision(incoming, defense) is expected


@pytest.mark.parametrize("point, expected", [
    ((100, 500), True),
    ((160, 500), True),
    ((100, 540), True),
    ((160, 540), True),
    ((130, 520), True),
    ((99.5, 520), False),
    ((160.5, 520), False),
    ((130, 499.5), False),
    ((130, 540.5), False),
])
def test_missile_to_building_is_inclusive_on_every_edge(point, expected):
    """A missile on any edge or corner of Building B hits it; 0.5 px outside misses."""
    missile = _stub(position=point)
    assert CollisionSystem.missile_to_building_collision(missile, _building_b()) is expected


@pytest.mark.parametrize("point, expected", [
    ((10, 10), True),
    ((70, 40), True),
    ((40, 25), True),
    ((70.5, 25), False),
    ((40, 9.5), False),
])
def test_missile_to_base_is_inclusive(point, expected):
    """The base check is an inclusive point-in-rect test against ``get_bounds()``."""
    base = _stub(get_bounds=lambda: pygame.Rect(10, 10, 60, 30))
    missile = _stub(position=point)
    assert CollisionSystem.missile_to_base_collision(missile, base) is expected


@pytest.mark.parametrize("x, y, expected", [
    (159, 500, True),
    (160, 500, False),   # shared vertical edge is not a collision
    (100, 539, True),
    (100, 540, False),   # shared horizontal edge is not a collision
])
def test_building_to_building_follows_colliderect(x, y, expected):
    """Building overlap uses ``Rect.colliderect``, so touching edges don't collide."""
    other = Building(x, y)
    assert CollisionSystem.building_to_building_collision(_building_b(), other) is expected


def test_building_to_building_with_itself():
    """A building collides with itself."""
    building = _building_b()
    assert CollisionSystem.building_to_building_collision(building, building) is True


@pytest.fixture
def explosion_r40():
    """A real ``Explosion(400, 300)`` advanced 0.25 s to radius exactly 40."""
    explosion = Explosion(400, 300)
    explosion.update(0.25)
    assert explosion.radius == 40
    return explosion


@pytest.mark.parametrize("point, expected", [
    ((440, 300), True),
    ((424, 332), True),
    ((400, 260), True),
    ((440.5, 300), False),
    ((400, 340.5), False),
])
def test_missile_in_explosion_is_inclusive(explosion_r40, point, expected):
    """A missile exactly ``radius`` from the blast centre is inside it."""
    missile = _stub(position=point)
    assert CollisionSystem.missile_in_explosion(missile, explosion_r40) is expected


@pytest.mark.parametrize("centre, radius, expected", [
    ((130, 520), 0, True),     # centre inside the rect
    ((200, 520), 40, True),
    ((200, 520), 39.5, False),
    ((163, 544), 5, True),     # corner case: nearest point (160, 540)
    ((163, 544), 4.9, False),
    ((130, 460), 40, True),
    ((130, 460), 39.5, False),
])
def test_building_to_explosion_uses_closest_point(centre, radius, expected):
    """The building/explosion check measures to the closest point on the building's rect."""
    explosion = _stub(position=centre, radius=radius)
    assert CollisionSystem.building_to_explosion(_building_b(), explosion) is expected


# --- MainGame.check_collisions boundaries -----------------------------------

@pytest.mark.parametrize("point, hit", [
    ((300, 400), True),
    ((360, 400), True),
    ((300, 440), True),
    ((360, 440), True),
    ((299.5, 420), False),
    ((360.5, 420), False),
    ((330, 399.5), False),
    ((330, 440.5), False),
])
def test_check_collisions_building_hit_box_is_inclusive(game, point, hit):
    """An enemy missile on any edge of a building hits it; 0.5 px outside misses."""
    building = Building(300, 400)
    game.buildings = [building]
    game.explosions = []
    missile = _park(game, *point)

    game.check_collisions()

    if hit:
        assert missile.is_destroyed
        assert building.health_current == 66
        assert len(game.explosions) == 1
        assert game.explosions[0].is_player is False
    else:
        assert not missile.is_destroyed
        assert building.health_current == 100
        assert game.explosions == []
    assert game.score_system.score == 0


def test_check_collisions_player_blast_radius_is_inclusive(game):
    """Missiles exactly ``radius`` from a player blast die; ones just outside survive."""
    blast = _player_blast(game, 400, 300, 0.25)
    assert blast.radius == 40
    on_edge = [_park(game, 440, 300), _park(game, 400, 260)]
    outside = [_park(game, 440.5, 300), _park(game, 376, 332.5)]  # ~40.4 away

    game.check_collisions()

    assert all(m.is_destroyed for m in on_edge)
    assert not any(m.is_destroyed for m in outside)
    assert game.score_system.score == 2 * MISSILE_INTERCEPT_POINTS
    assert game.score_system.total_missiles_hit == 2


def test_check_collisions_spent_player_blast_kills_nothing(game):
    """An inactive player blast still in ``explosions`` destroys nothing, even at its centre."""
    blast = _player_blast(game, 400, 300, EXPLOSION_EXPANSION_TIME + EXPLOSION_SHRINK_TIME + 0.01)
    assert blast.is_active is False
    assert blast.radius == 0
    missile = _park(game, 400, 300)

    game.check_collisions()

    assert blast in game.explosions
    assert not missile.is_destroyed
    assert game.score_system.score == 0


# --- ScoreSystem ------------------------------------------------------------

def test_add_missile_hit_default_and_custom_points(scores):
    """``add_missile_hit`` adds the default 10 or the given points and counts each hit."""
    scores.add_missile_hit()
    assert scores.score == MISSILE_INTERCEPT_POINTS == 10
    assert scores.total_missiles_hit == 1

    scores.add_missile_hit(25)
    assert scores.score == 35
    assert scores.total_missiles_hit == 2
    assert scores.buildings_destroyed == 0
    assert scores.time_survived == 0.0


def test_add_building_destroyed_adds_score_value(scores):
    """``add_building_destroyed`` adds the building's ``score_value`` and counts it."""
    scores.add_building_destroyed(Building(0, 0))
    assert scores.score == BUILDING_TYPES["residential"]["score_value"] == 50
    assert scores.buildings_destroyed == 1

    scores.add_building_destroyed(_stub(score_value=75))
    assert scores.score == 125
    assert scores.buildings_destroyed == 2
    assert scores.total_missiles_hit == 0


def test_mixed_total_then_reset_keeps_high_score(scores):
    """Hits, a building and survival time sum; ``reset()`` clears all but ``high_score``."""
    scores.high_score = 500
    for _ in range(3):
        scores.add_missile_hit()
    scores.add_building_destroyed(Building(0, 0))
    scores.add_survival_time(2.5)
    assert scores.score == 3 * 10 + 50 + 2 == 82

    scores.reset()
    assert scores.score == 0
    assert scores.total_missiles_hit == 0
    assert scores.buildings_destroyed == 0
    assert scores.time_survived == 0.0
    assert isinstance(scores.time_survived, float)
    assert scores.high_score == 500

    scores.add_survival_time(0.5)
    assert scores.score == 0
