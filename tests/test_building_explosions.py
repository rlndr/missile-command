"""Tests for job 018-building-explosions.

Covers the nearest-point distance check in ``CollisionSystem.building_in_explosion``
and the layered, flickering, fading fiery explosion spawned at a building's
centre when the third missile hit destroys it.
"""

import types

import pygame
import pytest

import game.constants as constants
from entities import Building, IncomingMissile
from entities.terrain import Explosion, ExplosionPool
from game.constants import (
    COLOR_BLACK,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_YELLOW,
    DT_DEFAULT,
    EXPLOSION_EXPANSION_TIME,
    EXPLOSION_MAX_RADIUS,
    EXPLOSION_SHRINK_TIME,
    MISSILE_INTERCEPT_POINTS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from systems.collision import CollisionSystem

Vector2 = pygame.math.Vector2


def _stub(x, y, r):
    """Return an explosion stub with ``position=Vector2(x, y)`` and ``radius=r``."""
    return types.SimpleNamespace(position=Vector2(x, y), radius=r)


def _building_b():
    """Return Building B: ``Building(100, 500)`` (60x40, bounds 100..160 x 500..540)."""
    return Building(100, 500)


def _black_surface_draw(explosion):
    """Draw ``explosion`` onto a fresh black ``(SCREEN_WIDTH, SCREEN_HEIGHT)`` surface."""
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surf.fill(COLOR_BLACK)
    explosion.draw_explosion(surf)
    return surf


def _park_missile(game, x, y):
    """Add a stationary ``IncomingMissile`` at ``(x, y)`` to ``game`` and return it."""
    missile = IncomingMissile(Vector2(x, y))
    missile.position = Vector2(x, y)
    missile.velocity = Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


# --- Criterion 1: Constants -------------------------------------------------


def test_building_explosion_constants():
    """Criterion 1: building explosion constants exist with their specified values."""
    assert constants.BUILDING_EXPLOSION_MAX_RADIUS == 110
    assert constants.BUILDING_EXPLOSION_MAX_RADIUS > EXPLOSION_MAX_RADIUS
    assert constants.BUILDING_EXPLOSION_EXPANSION_TIME == 0.4
    assert constants.BUILDING_EXPLOSION_SHRINK_TIME == 0.5
    assert constants.BUILDING_EXPLOSION_LAYERS == (
        (1.0, COLOR_RED),
        (0.7, COLOR_ORANGE),
        (0.4, COLOR_YELLOW),
    )
    assert constants.BUILDING_EXPLOSION_FLICKER_SPEED == 40.0
    assert constants.BUILDING_EXPLOSION_FLICKER_AMOUNT == 0.12


# --- Criterion 2: CollisionSystem.building_in_explosion ---------------------


@pytest.mark.parametrize("point, radius, expected", [
    ((130, 520), 30, True),     # centre inside building
    ((130, 520), 0, True),      # centre inside building, zero radius
    ((200, 520), 40, True),     # right edge
    ((200, 520), 39.5, False),
    ((70, 520), 30, True),      # left edge
    ((70, 520), 29.5, False),
    ((130, 460), 40, True),     # top edge
    ((130, 460), 39.5, False),
    ((130, 570), 30, True),     # bottom edge
    ((130, 570), 29.5, False),
    ((163, 544), 5, True),      # bottom-right corner (160, 540)
    ((163, 544), 4.9, False),
    ((97, 496), 5, True),       # top-left corner (100, 500)
    ((97, 496), 4.9, False),
])
def test_building_in_explosion_uses_nearest_point(point, radius, expected):
    """Criterion 2: ``building_in_explosion`` measures to the closest rect point."""
    b = _building_b()
    exp = _stub(point[0], point[1], radius)
    result = CollisionSystem.building_in_explosion(b, exp)
    assert result is expected
    assert result == CollisionSystem.building_to_explosion(b, exp)


# --- Criterion 3: Building explosion timeline and peak size -----------------


def test_building_explosion_timeline():
    """Criterion 3: building explosion expands over 0.4 s to 110 px and shrinks over 0.5 s."""
    e = Explosion(130, 520, is_building=True)
    assert e.is_building is True
    assert e.is_player is False
    assert e.radius == 0
    assert e.max_radius == constants.BUILDING_EXPLOSION_MAX_RADIUS == 110
    assert e.expansion_time == 0.4
    assert e.shrink_time == 0.5
    assert e.is_active is True

    # Half expansion (0.2 s)
    e.update(0.2)
    assert e.radius == pytest.approx(55.0)
    assert e.fade_alpha() == 255

    # Peak (0.4 s)
    e.update(0.2)
    assert e.radius == pytest.approx(110.0)
    assert e.radius > EXPLOSION_MAX_RADIUS
    assert e.fade_alpha() == 255

    # Halfway through shrink (0.65 s)
    e.update(0.25)
    assert e.radius == pytest.approx(55.0)
    assert e.fade_alpha() == pytest.approx(128, abs=1)

    # Expired (0.9 s)
    e.update(0.25)
    assert e.is_active is False
    assert e.radius == 0
    assert e.fade_alpha() == 0
    assert e.fire_layers() == []


# --- Criterion 4: Layered orange/yellow/red fire and flicker ----------------


def test_fire_layers_and_deterministic_flicker():
    """Criterion 4: 3 ordered fire layers that flicker over dt but are deterministic per frame."""
    e = Explosion(400, 300, is_building=True)
    e.update(0.4)
    layers = e.fire_layers()
    assert len(layers) == 3
    assert [color for _, color in layers] == [COLOR_RED, COLOR_ORANGE, COLOR_YELLOW]
    r_red, r_orange, r_yellow = [r for r, _ in layers]
    assert all(isinstance(r, int) for r in (r_red, r_orange, r_yellow))
    assert r_red > r_orange > r_yellow > 0
    assert r_red > EXPLOSION_MAX_RADIUS

    # Stepping across 6 frames of DT_DEFAULT from elapsed = 0.1 to ~0.2
    e_step = Explosion(400, 300, is_building=True)
    e_step.update(0.1)
    seen_triples = set()
    for _ in range(6):
        e_step.update(DT_DEFAULT)
        step_layers = e_step.fire_layers()
        triple = tuple(r for r, _ in step_layers)
        assert triple[0] > triple[1] > triple[2] > 0
        seen_triples.add(triple)
    assert len(seen_triples) >= 3

    # Deterministic when update() is not called
    layers_a = e.fire_layers()
    surf_a = _black_surface_draw(e)
    layers_b = e.fire_layers()
    surf_b = _black_surface_draw(e)
    assert layers_a == layers_b
    assert pygame.image.tostring(surf_a, "RGB") == pygame.image.tostring(surf_b, "RGB")


# --- Criterion 5: Rendered fire layers and fading on a surface --------------


def test_rendered_fire_layers_and_fade():
    """Criterion 5: concentric yellow/orange/red rings at peak and translucent fade during shrink."""
    e = Explosion(400, 300, is_building=True)
    e.update(0.4)
    surf_peak = _black_surface_draw(e)
    assert surf_peak.get_at((400, 300))[:3] == COLOR_YELLOW
    assert surf_peak.get_at((460, 300))[:3] == COLOR_ORANGE
    assert surf_peak.get_at((490, 300))[:3] == COLOR_RED
    assert surf_peak.get_at((530, 300))[:3] == COLOR_BLACK

    # Advance into shrink phase (elapsed == 0.65)
    e.update(0.25)
    assert e.fade_alpha() in (127, 128)
    surf_fade = _black_surface_draw(e)
    centre_rgb = surf_fade.get_at((400, 300))[:3]
    assert 115 <= centre_rgb[0] <= 140
    assert 115 <= centre_rgb[1] <= 140
    assert centre_rgb[0] < COLOR_YELLOW[0]
    assert centre_rgb[1] < COLOR_YELLOW[1]
    assert centre_rgb[0] > COLOR_BLACK[0]
    assert centre_rgb[1] > COLOR_BLACK[1]


# --- Criterion 6: Pool reuse resets is_building and timing fields -----------


def test_pool_reuse_resets_building_explosion_fields():
    """Criterion 6: reusing a pooled building explosion resets is_building and timing fields."""
    pool = ExplosionPool(pool_size=1)
    first = pool.get_explosion(130, 520, is_building=True)
    assert first.is_building is True
    assert first.max_radius == constants.BUILDING_EXPLOSION_MAX_RADIUS
    assert first.expansion_time == constants.BUILDING_EXPLOSION_EXPANSION_TIME
    assert first.shrink_time == constants.BUILDING_EXPLOSION_SHRINK_TIME

    first.update(0.3)
    pool.return_explosion(first)

    reused = pool.get_explosion(200, 200)
    assert reused is first
    assert reused.is_building is False
    assert reused.is_player is False
    assert reused.max_radius == EXPLOSION_MAX_RADIUS
    assert reused.expansion_time == EXPLOSION_EXPANSION_TIME
    assert reused.shrink_time == EXPLOSION_SHRINK_TIME
    assert reused.radius == 0
    assert reused.elapsed == 0.0
    assert reused.is_active is True
    assert reused.position == Vector2(200, 200)


# --- Criterion 7: Non-fatal vs fatal building hits in MainGame --------------


def test_non_fatal_vs_fatal_building_hits(main_game):
    """Criterion 7: hits 1-2 spawn regular explosions at impact point; hit 3 spawns building blast at centre."""
    game = main_game
    b = game.buildings[0]
    assert b.position == Vector2(30, 540)
    assert (b.width, b.height) == (60, 40)

    # Hit 1 at top-left corner (30, 540)
    _park_missile(game, 30, 540)
    game.check_collisions()
    assert b.health_current == 66
    assert not b.is_destroyed
    assert len(game.explosions) == 1
    exp1 = game.explosions[-1]
    assert exp1.is_building is False
    assert exp1.is_player is False
    assert exp1.max_radius == EXPLOSION_MAX_RADIUS
    assert exp1.position == Vector2(30, 540)

    # Hit 2 at top-left corner (30, 540)
    _park_missile(game, 30, 540)
    game.check_collisions()
    assert b.health_current == 32
    assert not b.is_destroyed
    assert len(game.explosions) == 2
    exp2 = game.explosions[-1]
    assert exp2.is_building is False
    assert exp2.is_player is False
    assert exp2.max_radius == EXPLOSION_MAX_RADIUS
    assert exp2.position == Vector2(30, 540)

    # Hit 3 (fatal) at top-left corner (30, 540) -> explosion at building centre (60, 560)
    _park_missile(game, 30, 540)
    game.check_collisions()
    assert b.health_current == 0
    assert b.is_destroyed is True
    assert len(game.explosions) == 3
    exp3 = game.explosions[-1]
    assert exp3.is_building is True
    assert exp3.is_player is False
    assert exp3.max_radius == constants.BUILDING_EXPLOSION_MAX_RADIUS
    assert exp3.position == Vector2(60, 560)


# --- Criterion 8: Building explosion does not intercept or harm neighbours ---


def test_building_explosion_harmless_to_missiles_and_adjacent_buildings(main_game):
    """Criterion 8: a peak building fireball neither damages neighbours nor intercepts missiles."""
    game = main_game
    b0 = game.buildings[0]
    b1 = game.buildings[1]
    assert b1.position == Vector2(110, 540)

    for _ in range(3):
        _park_missile(game, 30, 540)
        game.check_collisions()

    assert b0 not in game.buildings
    assert b1 in game.buildings
    assert b1.health_current == 100

    game.update(0.4)
    building_blasts = [e for e in game.explosions if e.is_building]
    assert len(building_blasts) == 1
    assert building_blasts[0].radius == pytest.approx(110.0)

    score_before = game.score_system.score
    parked = _park_missile(game, 60, 500)
    game.check_collisions()

    assert not parked.is_destroyed
    assert b1.health_current == 100
    assert game.score_system.score == score_before
    assert game.score_system.score < score_before + MISSILE_INTERCEPT_POINTS


# --- Criterion 9: In-game rendering of a destroyed building's fireball ------


def test_in_game_rendering_of_destroyed_building_fireball(main_game):
    """Criterion 9: drawing the game at peak building explosion shows yellow core, orange mid, red outer."""
    game = main_game
    game.explosions.clear()
    b0 = game.buildings[0]
    b0.health_current = 34

    _park_missile(game, 60, 560)
    game.check_collisions()
    assert b0.is_destroyed is True

    game.update(0.4)
    game.draw()

    assert game.screen.get_at((60, 560))[:3] == COLOR_YELLOW
    assert game.screen.get_at((60, 500))[:3] == COLOR_ORANGE
    assert game.screen.get_at((60, 470))[:3] == COLOR_RED
