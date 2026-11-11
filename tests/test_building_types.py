"""Tests for job 002-fix-building-health-bar: bar colours and the new building types.

The building health bar fill is green, yellow or red by health band instead
of a bare int that pygame drew as blue. ``BUILDING_TYPES`` gains industrial
and military buildings, which fit the existing 8-building city layout.
"""

import random

import pygame
import pytest

import game.constants
import systems.game_loop
import systems.score
from entities import Building
from game.constants import (BUILDING_INDUSTRIAL_COLOR, BUILDING_MILITARY_COLOR,
                            BUILDING_TYPES, COLOR_BLACK, GROUND_Y,
                            HEALTH_BAR_CRITICAL_COLOR, HEALTH_BAR_DAMAGED_COLOR,
                            HEALTH_BAR_HEALTHY_COLOR, SCREEN_HEIGHT, SCREEN_WIDTH)
from systems.score import ScoreSystem

GREEN = HEALTH_BAR_HEALTHY_COLOR
YELLOW = HEALTH_BAR_DAMAGED_COLOR
RED = HEALTH_BAR_CRITICAL_COLOR
LEFT_XS = [30, 110, 190, 270]
RIGHT_EDGES = [530, 610, 690, 770]


def _bar_pixel(building):
    """Draw ``building`` on a fresh black screen-sized surface; return the RGB inside the bar fill."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(COLOR_BLACK)
    building.draw_building(surface)
    x, y = int(building.position.x), int(building.position.y)
    return tuple(surface.get_at((x + 3, y - 3)))[:3]


def _check_city(game):
    """Assert the city meets the ground, has no overlaps and stays clear of the tower."""
    buildings = game.buildings
    assert len(buildings) == 8
    body = game.base.get_bounds()
    barrel = game.base.barrel_rect()
    for b in buildings:
        bounds = b.get_bounds()
        assert bounds.bottom == GROUND_Y
        assert b.position.y == GROUND_Y - b.height
        assert not bounds.colliderect(body)
        assert not bounds.colliderect(barrel)
        assert bounds.right <= 330 or bounds.left >= 470
    for i, a in enumerate(buildings):
        for b in buildings[i + 1:]:
            assert not a.get_bounds().colliderect(b.get_bounds())


# 10a
@pytest.mark.parametrize("health, expected", [
    (90, GREEN),
    (76, GREEN),
    (75, YELLOW),   # exactly 0.75 is not healthy
    (70, YELLOW),
    (66, YELLOW),
    (65, RED),      # exactly 0.65 is not damaged
    (60, RED),
])
def test_health_bar_color_bands(health, expected):
    """``health_bar_color()`` is green above 0.75, yellow above 0.65 and red otherwise."""
    building = Building(100, 500)
    building.health_current = health
    assert building.health_bar_color() == expected


# 10b
@pytest.mark.parametrize("health, expected", [(90, GREEN), (70, YELLOW), (60, RED)])
def test_drawn_bar_fill_colour(health, expected):
    """The drawn bar fill uses the band colour, not a packed-int blue."""
    building = Building(100, 500)
    building.health_current = health
    assert _bar_pixel(building) == expected


# 10c
@pytest.mark.parametrize("name, expected", [
    ("industrial", (BUILDING_INDUSTRIAL_COLOR, 150, 75, 4, 60, 30)),
    ("military", (BUILDING_MILITARY_COLOR, 200, 100, 5, 44, 56)),
])
def test_new_type_stats(name, expected):
    """Industrial and military have the agreed stats, and a colour no other type uses."""
    config = BUILDING_TYPES[name]
    keys = ("color", "health_max", "score_value", "damage_threshold", "width", "height")
    assert tuple(config[k] for k in keys) == expected
    building = Building(0, 0, name)
    assert (building.color, building.health_max, building.score_value,
            building.damage_threshold, building.width, building.height) == expected
    others = [c["color"] for k, c in BUILDING_TYPES.items() if k != name]
    assert config["color"] not in others


def test_building_type_order():
    """The types are residential, industrial and military, in that order."""
    assert list(BUILDING_TYPES) == ["residential", "industrial", "military"]


# 10d
@pytest.mark.parametrize("name, healths, colours", [
    ("residential", [66, 32, 0], {66: YELLOW}),
    ("industrial", [112, 74, 36, 0], {112: YELLOW}),
    ("military", [160, 120, 80, 40, 0], {160: GREEN, 120: RED}),
])
def test_impact_sequences(name, healths, colours):
    """Each impact takes the expected health; the last one destroys the building."""
    building = Building(100, 500, name)
    for i, health in enumerate(healths):
        assert building.is_active()
        building.take_impact()
        assert building.health_current == health
        if health in colours:
            assert building.health_bar_color() == colours[health]
            assert _bar_pixel(building) == colours[health]
        assert building.is_active() == (i < len(healths) - 1)


# 10e
@pytest.mark.parametrize("name, points", [("industrial", 75), ("military", 100)])
def test_score_for_destroying_new_types(monkeypatch, tmp_path, name, points):
    """``add_building_destroyed`` adds the type's score value."""
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    scores = ScoreSystem()
    assert scores.score == 0
    scores.add_building_destroyed(Building(0, 0, name))
    assert scores.score == points


# 10f
@pytest.mark.parametrize("name", ["residential", "industrial", "military"])
def test_layout_per_type(main_game, monkeypatch, name):
    """A city of one type sits on the ground at the agreed x positions, clear of the tower."""
    monkeypatch.setattr(systems.game_loop, "BUILDING_TYPES", {name: BUILDING_TYPES[name]})
    main_game.start_game()
    _check_city(main_game)
    assert all(b.building_type == name for b in main_game.buildings)
    assert [b.position.x for b in main_game.buildings[:4]] == LEFT_XS
    assert [b.get_bounds().right for b in main_game.buildings[4:]] == RIGHT_EDGES


# 10g
def test_mixed_layout(main_game, monkeypatch):
    """Cities drawn from every type stay valid across seeds, and every type appears."""
    monkeypatch.setattr(systems.game_loop, "BUILDING_TYPES", game.constants.BUILDING_TYPES)
    seen = set()
    for seed in range(20):
        random.seed(seed)
        main_game.start_game()
        _check_city(main_game)
        seen.update(b.building_type for b in main_game.buildings)
    assert seen == {"residential", "industrial", "military"}
