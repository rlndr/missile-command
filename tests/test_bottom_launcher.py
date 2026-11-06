"""Tests for job 009-bottom-launcher: a launcher tower on the ground at the bottom centre.

The launcher moves from the top-left corner to a tower standing on a ground
strip in the middle of the bottom edge. The city splits into two mirrored
halves either side of it, and defense missiles rise from the tower's barrel.
"""

import gc
import inspect

import pygame
import pytest

import entities.base
import entities.missile
import game.constants as constants
import systems.game_loop
import systems.score
from entities import DefenseMissile, DefensiveBase
from game.constants import (COLOR_BLACK, COLOR_GRAY, COLOR_WHITE, COLOR_YELLOW,
                            DEFENSE_MISSILE_SPEED, DT_DEFAULT, SCREEN_HEIGHT,
                            SCREEN_WIDTH, STATE_PAUSED, STATE_START)
from systems.game_loop import MainGame

Vector2 = pygame.math.Vector2
FIRE = {"fire_missile": (400, 300)}
SCREEN = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)


def _c(name):
    """Look up a constant lazily, so a missing name fails the one test that needs it."""
    return getattr(constants, name)


def _px(surface, x, y):
    """Return the RGB of the pixel at ``(x, y)``."""
    return tuple(surface.get_at((x, y)))[:3]


def _surface_draw(base):
    """Draw ``base`` on a fresh black screen-sized surface and return the surface."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(COLOR_BLACK)
    base.draw_base(surface)
    return surface


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
    """Ground, launcher and city layout constants have the agreed values and types."""
    expected = {
        "GROUND_HEIGHT": 20,
        "GROUND_Y": 580,
        "LAUNCHER_WIDTH": 60,
        "LAUNCHER_HEIGHT": 50,
        "LAUNCHER_BARREL_WIDTH": 8,
        "LAUNCHER_BARREL_HEIGHT": 16,
        "LAUNCHER_X": 400,
        "LAUNCHER_Y": 514,
        "CITY_EDGE_MARGIN": 30,
        "BUILDING_SPACING": 80,
    }
    for name, value in expected.items():
        assert _c(name) == value, name
        assert type(_c(name)) is int, name
    assert _c("GROUND_Y") == SCREEN_HEIGHT - _c("GROUND_HEIGHT")
    assert _c("LAUNCHER_X") == SCREEN_WIDTH // 2
    assert _c("LAUNCHER_Y") == (_c("GROUND_Y") - _c("LAUNCHER_HEIGHT")
                                - _c("LAUNCHER_BARREL_HEIGHT"))

    ground = _c("COLOR_GROUND")
    assert isinstance(ground, tuple) and len(ground) == 3
    assert all(type(c) is int and 0 <= c <= 255 for c in ground)
    for other in ("COLOR_BLUE", "COLOR_DARK_BLUE", "COLOR_GRAY", "COLOR_WHITE",
                  "COLOR_BLACK", "COLOR_ORANGE", "COLOR_YELLOW"):
        assert ground != _c(other), other

    assert not hasattr(constants, "LAUNCHER_X_OFFSET")
    assert not hasattr(constants, "LAUNCHER_Y_OFFSET")


# Criterion 2
def test_tower_geometry():
    """The muzzle is at (400, 514), the body stands on the ground and the barrel sits on it."""
    base = DefensiveBase()
    assert base.position == Vector2(400, 514)
    body = base.get_bounds()
    assert body == pygame.Rect(370, 530, 60, 50)
    assert body.bottom == _c("GROUND_Y")
    assert body.centerx == _c("LAUNCHER_X")
    barrel = base.barrel_rect()
    assert barrel == pygame.Rect(396, 514, 8, 16)
    assert barrel.bottom == body.top
    assert barrel.midtop == (400, 514)
    assert SCREEN.contains(body)
    assert SCREEN.contains(barrel)


# Criterion 3
def test_reload_bar_in_ground_strip():
    """The reload bar sits under the body, inside the ground strip."""
    base = DefensiveBase()
    track = base.cooldown_bar_rects()[0]
    assert track == pygame.Rect(370, 584, 60, 4)
    assert track.top >= _c("GROUND_Y")
    assert track.bottom <= SCREEN_HEIGHT
    assert not track.colliderect(base.get_bounds())


# Criterion 4
def test_city_layout(main_game):
    """Two mirrored groups of four buildings stand on the ground, clear of the tower."""
    game = main_game
    game.start_game()
    xs = [b.position.x for b in game.buildings]
    assert xs == [30, 110, 190, 270, 470, 550, 630, 710]
    assert all(b.position.y == 540 for b in game.buildings)

    body = game.base.get_bounds()
    barrel = game.base.barrel_rect()
    for b in game.buildings:
        bounds = b.get_bounds()
        assert bounds.bottom == _c("GROUND_Y")
        assert not bounds.colliderect(body)
        assert not bounds.colliderect(barrel)
        assert bounds.right <= 330 or bounds.left >= 470

    buildings = game.buildings
    for i in range(8):
        assert buildings[i].position.x + buildings[i].width + buildings[7 - i].position.x \
            == SCREEN_WIDTH

    game.start_game()
    assert [b.position.x for b in game.buildings] == xs
    assert all(b.position.y == 540 for b in game.buildings)


# Criterion 5
def test_missiles_start_at_muzzle(main_game):
    """Defense missiles start at the muzzle, and a shot at (400, 300) flies straight up."""
    m = DefenseMissile(Vector2(400, 300))
    assert m.position == Vector2(_c("LAUNCHER_X"), _c("LAUNCHER_Y"))
    assert m.velocity == Vector2(0, -DEFENSE_MISSILE_SPEED)

    main_game.handle_actions(FIRE)
    assert len(main_game.defense_missiles) == 1
    assert main_game.defense_missiles[0].position == main_game.base.position


# Criterion 6
@pytest.mark.parametrize("target", [(400, 300), (50, 50), (750, 50), (100, 500), (700, 513)])
def test_missiles_rise_toward_targets(target):
    """Missiles aimed above the muzzle never move down, stay on screen and land on target."""
    target = Vector2(target)
    m = DefenseMissile(target)
    assert m.velocity.y < 0
    previous_y = m.position.y
    for _ in range(200):
        m.update(DT_DEFAULT)
        assert m.position.y <= previous_y
        assert 0 <= m.position.x <= SCREEN_WIDTH
        assert 0 <= m.position.y <= SCREEN_HEIGHT
        previous_y = m.position.y
        if m.reached_target:
            break
    assert m.reached_target is True
    assert m.position == target


# Criterion 7
def test_flight_time(main_game):
    """A 214 px shot straight up arrives on the 34th update, alone and through the game."""
    m = DefenseMissile(Vector2(400, 300))
    for _ in range(33):
        m.update(DT_DEFAULT)
    assert m.reached_target is False
    m.update(DT_DEFAULT)
    assert m.reached_target is True

    game = main_game
    game.spawn_defense_missile((400, 300))
    for _ in range(33):
        game.update(DT_DEFAULT)
    assert game.explosions == []
    game.update(DT_DEFAULT)
    assert len(game.explosions) == 1
    assert game.explosions[0].is_player is True
    assert game.explosions[0].position == Vector2(400, 300)


# Criterion 8
def test_tower_pixels():
    """Body and barrel are drawn in the body colour, with nothing around them but the bar."""
    ready = _c("COOLDOWN_BAR_READY_COLOR")
    base = DefensiveBase()
    base.reset()
    surface = _surface_draw(base)
    assert _px(surface, 400, 555) == COLOR_WHITE
    assert _px(surface, 400, 520) == COLOR_WHITE
    for x, y in [(400, 512), (390, 520), (369, 555), (430, 555)]:
        assert _px(surface, x, y) == COLOR_BLACK, (x, y)
    assert _px(surface, 370, 585) == ready
    assert _px(surface, 429, 585) == ready
    assert _px(surface, 400, 582) == COLOR_BLACK

    base.is_active = False
    surface = _surface_draw(base)
    assert _px(surface, 400, 555) == COLOR_GRAY
    assert _px(surface, 400, 520) == COLOR_GRAY


# Criterion 9
def test_ground_and_tower_in_game_frame(main_game):
    """The game frame shows the ground strip, the tower, the bar and a building in each half."""
    game = main_game
    game.draw()
    screen = game.screen
    ground = _c("COLOR_GROUND")
    for x, y in [(5, 590), (795, 590), (400, 598), (400, 582)]:
        assert _px(screen, x, y) == ground, (x, y)
    assert _px(screen, 5, 578) != ground
    assert _px(screen, 400, 555) == COLOR_WHITE
    assert _px(screen, 400, 520) == COLOR_WHITE
    assert _px(screen, 375, 585) == _c("COOLDOWN_BAR_READY_COLOR")
    assert _px(screen, 60, 560) == COLOR_GRAY
    assert _px(screen, 740, 560) == COLOR_GRAY


# Criterion 10
def test_bar_works_in_game_frame(main_game):
    """The bar under the tower fills while reloading and turns yellow when ready."""
    game = main_game
    game.handle_actions(FIRE)
    game.update(0.75)
    game.draw()
    assert _px(game.screen, 375, 585) == _c("COOLDOWN_BAR_FILL_COLOR")
    assert _px(game.screen, 415, 585) == _c("COOLDOWN_BAR_TRACK_COLOR")
    game.update(1.0)
    game.draw()
    assert _px(game.screen, 375, 585) == _c("COOLDOWN_BAR_READY_COLOR")
    assert _px(game.screen, 415, 585) == _c("COOLDOWN_BAR_READY_COLOR")


# Criterion 11
def test_rising_missile_drawn_above_tower(main_game):
    """After 17 frames the missile is about 107 px above the muzzle and drawn yellow there."""
    game = main_game
    game.handle_actions(FIRE)
    for _ in range(17):
        game.update(DT_DEFAULT)
    game.draw()
    m = game.defense_missiles[0]
    assert m.position.x == pytest.approx(400)
    assert m.position.y == pytest.approx(406, abs=1)
    assert _px(game.screen, int(m.position.x), int(m.position.y)) == COLOR_YELLOW
    assert _px(game.screen, 400, 406) == COLOR_YELLOW


# Criterion 12
def test_not_on_menu_screens(start_screen_game):
    """The start and pause screens draw neither ground nor tower."""
    game = start_screen_game
    game.draw_start_screen()
    assert _px(game.screen, 5, 590) != _c("COLOR_GROUND")
    assert _px(game.screen, 400, 555) != COLOR_WHITE
    game.state = STATE_PAUSED
    game.draw_start_screen()
    assert _px(game.screen, 5, 590) != _c("COLOR_GROUND")
    assert _px(game.screen, 400, 555) != COLOR_WHITE


# Criterion 13
def test_no_top_left_leftovers():
    """No module still refers to the old top-left launcher offsets."""
    for module in (entities.base, entities.missile, systems.game_loop):
        source = inspect.getsource(module)
        assert "LAUNCHER_X_OFFSET" not in source, module.__name__
        assert "LAUNCHER_Y_OFFSET" not in source, module.__name__
    assert "top-left" not in inspect.getsource(entities.base)

