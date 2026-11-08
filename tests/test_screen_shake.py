"""Regression and unit tests for screen shake (job 001-fix-shake-crash).

Before the fix, ``MainGame.draw()`` passed the decayed float
``shake_intensity`` straight to ``random.randint`` and crashed the frame
after any building hit or intercept.
"""

import os
import random
from pathlib import Path

import pygame
import pytest

import systems.score
from entities import DefenseMissile, IncomingMissile
from entities.terrain import Explosion
from game.constants import (
    COOLDOWN_BAR_GAP,
    COOLDOWN_BAR_READY_COLOR,
    COLOR_BLUE,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GROUND,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    DT_DEFAULT,
    ENEMY_TRAIL_HEAD_COLOR,
    GROUND_Y,
    LAUNCHER_X,
    LAUNCHER_Y,
    SCREEN_HEIGHT,
    SCREEN_SHAKE_BUILDING_HIT,
    SCREEN_SHAKE_DECAY_RATE,
    SCREEN_SHAKE_INTERCEPT,
    SCREEN_WIDTH,
)


def _sky_color(y):
    """Return the expected unshifted night-sky gradient RGB tuple at row ``y``."""
    intensity = int(
        COLOR_BLUE[1] + (y / SCREEN_HEIGHT) * (COLOR_DARK_BLUE[1] - COLOR_BLUE[1])
    )
    return (COLOR_BLUE[0], intensity, COLOR_BLUE[2])


def _place_missile_on_building(game):
    """Replace incoming missiles with one sitting at the centre of buildings[0]."""
    building = game.buildings[0]
    game.incoming_missiles = []
    missile = IncomingMissile(pygame.math.Vector2(building.position.x, building.position.y))
    missile.position = building.position + pygame.math.Vector2(
        building.width / 2, building.height / 2
    )
    game.incoming_missiles.append(missile)
    return missile


def _frame(game):
    """Run one game-loop frame: update, check collisions, draw."""
    game.update(DT_DEFAULT)
    game.check_collisions()
    game.draw()


def test_building_hit_does_not_crash_on_following_frames(main_game):
    """Criteria 1 and 2: building hit, then 10 frames through the float shake path."""
    random.seed(0)
    game = main_game
    missile = _place_missile_on_building(game)

    # Frame 1: the hit.
    game.update(DT_DEFAULT)
    game.check_collisions()
    assert missile.is_destroyed is True
    assert game.shake_intensity == SCREEN_SHAKE_BUILDING_HIT
    game.draw()

    # Frame 2: decay makes the intensity a non-integer float; draw must survive it.
    game.update(DT_DEFAULT)
    assert isinstance(game.shake_intensity, float)
    assert game.shake_intensity != int(game.shake_intensity)
    game.check_collisions()
    game.draw()

    # Frames 3-10.
    for _ in range(8):
        _frame(game)


@pytest.mark.parametrize("intensity", [4.5, 0.01, SCREEN_SHAKE_INTERCEPT - 0.25])
def test_draw_with_fractional_shake_intensity(main_game, intensity):
    """Criterion 3: draw() succeeds for fractional intensities."""
    random.seed(0)
    main_game.shake_intensity = intensity
    main_game.draw()


def test_get_shake_offset_returns_bounded_ints(main_game):
    """Criterion 4: offsets are plain ints within [-ceil(A), ceil(A)]."""
    random.seed(0)
    main_game.shake_intensity = 4.97
    for _ in range(200):
        offset = main_game.get_shake_offset()
        assert isinstance(offset, tuple)
        assert len(offset) == 2
        for v in offset:
            assert type(v) is int
            assert -5 <= v <= 5


@pytest.mark.parametrize("intensity", [0, 0.0])
def test_get_shake_offset_zero_when_no_shake(main_game, intensity):
    """Criterion 5: no intensity means no offset."""
    main_game.shake_intensity = intensity
    assert main_game.get_shake_offset() == (0, 0)


def test_shake_decays_to_zero_after_building_hit(main_game):
    """Criterion 6: shake fully decays well within 160 frames."""
    random.seed(0)
    game = main_game
    missile = _place_missile_on_building(game)
    game.update(DT_DEFAULT)
    game.check_collisions()
    assert missile.is_destroyed is True
    assert game.shake_intensity == SCREEN_SHAKE_BUILDING_HIT

    frames = 160
    assert frames * DT_DEFAULT > SCREEN_SHAKE_BUILDING_HIT / SCREEN_SHAKE_DECAY_RATE
    for _ in range(frames):
        game.update(DT_DEFAULT)
    assert game.shake_intensity == 0
    game.draw()


def test_intercept_sets_shake_and_next_frame_draws(main_game):
    """Criterion 7: an intercept sets intercept shake and the next frame survives.

    Since job 002 an intercept comes from a player explosion catching an
    incoming missile inside its current radius, not from missile contact.
    """
    random.seed(0)
    game = main_game
    game.incoming_missiles = []
    game.defense_missiles = []

    explosion = game.explosion_pool.get_explosion(400, 200, is_player=True)
    explosion.update(0.25)
    game.explosions = [explosion]

    incoming = IncomingMissile(pygame.math.Vector2(400, 300))
    incoming.position = pygame.math.Vector2(408, 208)
    game.incoming_missiles.append(incoming)

    game.check_collisions()
    assert incoming.is_destroyed is True
    assert game.shake_intensity == SCREEN_SHAKE_INTERCEPT

    game.update(DT_DEFAULT)
    assert isinstance(game.shake_intensity, float)
    assert game.shake_intensity != int(game.shake_intensity)
    game.draw()


def test_harness_isolates_config_and_display(main_game, tmp_path):
    """Criterion 8: config path is under tmp_path and SDL runs headless."""
    config_path = Path(systems.score.CONFIG_PATH).resolve()
    assert config_path.is_relative_to(tmp_path.resolve())
    assert os.environ["SDL_VIDEODRIVER"] == "dummy"
    assert os.environ["SDL_AUDIODRIVER"] == "dummy"


def test_single_offset_per_frame_in_draw_scene(main_game, monkeypatch):
    """020 Criterion 1: draw_scene() calls get_shake_offset() once and shares the offset."""
    game = main_game
    calls = []
    offsets = [(6, -6), (-6, 6)]

    def fake_get_shake_offset():
        idx = min(len(calls), len(offsets) - 1)
        offset = offsets[idx]
        calls.append(offset)
        return offset

    monkeypatch.setattr(game, "get_shake_offset", fake_get_shake_offset)
    game.draw_scene()

    assert len(calls) == 1
    assert game.screen.get_at((350, GROUND_Y - 4))[:3] == COLOR_GROUND
    assert game.screen.get_at((406, 520))[:3] == COLOR_WHITE
    assert game.screen.get_at((94, 564))[:3] == COLOR_GRAY


def test_zero_shake_is_pixel_identical(main_game):
    """020 Criterion 2: zero shake renders battlefield elements at unshifted coordinates."""
    game = main_game
    game.shake_intensity = 0
    assert game.get_shake_offset() == (0, 0)

    game.draw_scene()

    assert game.screen.get_at((350, GROUND_Y + 3))[:3] == COLOR_GROUND
    assert game.screen.get_at((LAUNCHER_X, LAUNCHER_Y + 6))[:3] == COLOR_WHITE
    assert (
        game.screen.get_at((LAUNCHER_X, GROUND_Y + COOLDOWN_BAR_GAP + 1))[:3]
        == COOLDOWN_BAR_READY_COLOR
    )
    assert game.screen.get_at((60, 570))[:3] == COLOR_GRAY


def test_ground_shifts_with_shake_offset(main_game, monkeypatch):
    """020 Criterion 3: ground strip shifts vertically with (shake_x, shake_y)."""
    game = main_game

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, 0))
    game.draw_scene()
    assert game.screen.get_at((350, GROUND_Y - 4))[:3] == _sky_color(GROUND_Y - 4)

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, -6))
    game.draw_scene()
    assert game.screen.get_at((350, GROUND_Y - 4))[:3] == COLOR_GROUND

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, 6))
    game.draw_scene()
    assert game.screen.get_at((350, GROUND_Y + 3))[:3] == _sky_color(GROUND_Y + 3)
    assert game.screen.get_at((350, GROUND_Y + 8))[:3] == COLOR_GROUND


def test_launcher_body_barrel_and_reload_bar_shift_with_shake_offset(
    main_game, monkeypatch
):
    """020 Criterion 4: launcher body, barrel, and reload bar shift with (shake_x, shake_y)."""
    game = main_game
    monkeypatch.setattr(game, "get_shake_offset", lambda: (6, -6))

    game.draw_scene()

    # Barrel shifted right by 6 and up by 6
    assert game.screen.get_at((406, 520))[:3] == COLOR_WHITE
    assert game.screen.get_at((398, 520))[:3] == _sky_color(520)
    # Launcher body shifted right by 6 and up by 6 (unshifted x in [370, 430), y in [530, 580))
    assert game.screen.get_at((434, 550))[:3] == COLOR_WHITE
    assert game.screen.get_at((372, 550))[:3] == _sky_color(550)
    # Ready reload bar shifted right by 6 and up by 6 (unshifted y in [584, 588))
    assert game.screen.get_at((400, 579))[:3] == COOLDOWN_BAR_READY_COLOR


def test_buildings_shift_with_shake_offset(main_game, monkeypatch):
    """020 Criterion 5: buildings shift with (shake_x, shake_y)."""
    game = main_game

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, 0))
    game.draw_scene()
    assert game.screen.get_at((31, 570))[:3] == COLOR_GRAY
    assert game.screen.get_at((94, 570))[:3] == _sky_color(570)

    monkeypatch.setattr(game, "get_shake_offset", lambda: (6, 0))
    game.draw_scene()
    assert game.screen.get_at((94, 570))[:3] == COLOR_GRAY
    assert game.screen.get_at((31, 570))[:3] == _sky_color(570)


def test_missiles_and_trails_shift_with_shake_offset(main_game, monkeypatch):
    """020 Criterion 6: defense missiles, incoming missiles, and enemy trails shift."""
    game = main_game
    game.incoming_missiles = []
    game.defense_missiles = []
    game.explosions = []

    defense = DefenseMissile(pygame.math.Vector2(200, 100))
    defense.position = pygame.math.Vector2(200, 300)
    game.defense_missiles = [defense]

    # Confirm 2-arg draw_missile(missile, color) still works directly
    game.draw_missile(defense, COLOR_YELLOW)
    assert game.screen.get_at((200, 300))[:3] == COLOR_YELLOW

    monkeypatch.setattr(game, "get_shake_offset", lambda: (8, -7))
    game.draw_scene()
    assert game.screen.get_at((208, 293))[:3] == COLOR_YELLOW
    assert game.screen.get_at((200, 300))[:3] == _sky_color(300)

    game.defense_missiles = []
    incoming = IncomingMissile(pygame.math.Vector2(500, 500))
    incoming.position = pygame.math.Vector2(500, 250)
    incoming.trail.clear()
    incoming.trail.append(pygame.math.Vector2(500, 200))
    game.incoming_missiles = [incoming]

    monkeypatch.setattr(game, "get_shake_offset", lambda: (7, -5))
    game.draw_scene()
    assert game.screen.get_at((507, 245))[:3] == COLOR_RED
    assert game.screen.get_at((495, 250))[:3] == _sky_color(250)
    assert game.screen.get_at((507, 215))[:3] == ENEMY_TRAIL_HEAD_COLOR
    assert game.screen.get_at((507, 215))[:3] == COLOR_ORANGE
    assert game.screen.get_at((500, 220))[:3] == _sky_color(220)


def test_explosions_shift_with_shake_offset(main_game, monkeypatch):
    """020 Criterion 7: standard ring explosions and building fireballs shift."""
    game = main_game
    game.incoming_missiles = []
    game.defense_missiles = []

    std_exp = Explosion(300, 200, is_building=False)
    std_exp.radius = 10
    game.explosions = [std_exp]

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, 0))
    game.draw_scene()
    centre_color = game.screen.get_at((300, 200))[:3]
    assert centre_color == (75, 75, 140)
    assert centre_color != _sky_color(200)

    monkeypatch.setattr(game, "get_shake_offset", lambda: (8, -8))
    game.draw_scene()
    assert game.screen.get_at((308, 192))[:3] == centre_color
    assert game.screen.get_at((295, 205))[:3] == _sky_color(205)

    bld_exp = Explosion(300, 250, is_building=True)
    bld_exp.elapsed = 0.2
    bld_exp.radius = 10
    game.explosions = [bld_exp]

    game.draw_scene()
    assert game.screen.get_at((308, 242))[:3] == COLOR_YELLOW
    assert game.screen.get_at((300, 250))[:3] != COLOR_YELLOW


def test_hud_stays_stationary_and_sky_fills_exposed_edges(main_game, monkeypatch):
    """020 Criterion 8: top 60px strip (HUD + sky) is identical and exposed left edge is sky."""
    game = main_game
    game.incoming_missiles = []
    game.defense_missiles = []
    game.explosions = []

    top_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 60)

    monkeypatch.setattr(game, "get_shake_offset", lambda: (0, 0))
    game.draw_scene()
    unshifted_top = pygame.image.tostring(game.screen.subsurface(top_rect), "RGB")

    monkeypatch.setattr(game, "get_shake_offset", lambda: (8, -8))
    game.draw_scene()
    shifted_top = pygame.image.tostring(game.screen.subsurface(top_rect), "RGB")

    assert shifted_top == unshifted_top
    assert game.screen.get_at((2, 300))[:3] == _sky_color(300)
    assert game.screen.get_at((2, 300))[:3] != (0, 0, 0)
    assert game.screen.get_at((2, GROUND_Y + 3))[:3] == _sky_color(GROUND_Y + 3)


def test_draw_scene_does_not_mutate_state_during_shake(main_game):
    """020 Criterion 9: draw_scene() leaves game and entity state untouched during shake."""
    random.seed(42)
    game = main_game
    game.shake_intensity = SCREEN_SHAKE_INTERCEPT
    game.game_time = 12.5
    game.score_system.score = 130

    defense = DefenseMissile(pygame.math.Vector2(220, 180))
    defense.position = pygame.math.Vector2(210, 310)
    game.defense_missiles = [defense]

    incoming = IncomingMissile(pygame.math.Vector2(500, 500))
    incoming.position = pygame.math.Vector2(480, 220)
    incoming.trail.clear()
    incoming.trail.append(pygame.math.Vector2(480, 190))
    incoming.trail.append(pygame.math.Vector2(480, 205))
    game.incoming_missiles = [incoming]

    exp1 = Explosion(300, 200, is_building=False)
    exp1.radius = 15
    exp2 = Explosion(350, 260, is_building=True)
    exp2.elapsed = 0.2
    exp2.radius = 25
    game.explosions = [exp1, exp2]

    base_pos_before = pygame.math.Vector2(game.base.position)
    building_positions_before = [pygame.math.Vector2(b.position) for b in game.buildings]
    defense_pos_before = pygame.math.Vector2(defense.position)
    incoming_pos_before = pygame.math.Vector2(incoming.position)
    trail_before = [pygame.math.Vector2(p) for p in incoming.trail]
    exp_state_before = [(pygame.math.Vector2(e.position), e.radius, e.elapsed) for e in game.explosions]

    game.draw_scene()

    assert game.shake_intensity == SCREEN_SHAKE_INTERCEPT
    assert game.game_time == 12.5
    assert game.score_system.score == 130
    assert game.base.position == base_pos_before
    assert [b.position for b in game.buildings] == building_positions_before
    assert defense.position == defense_pos_before
    assert incoming.position == incoming_pos_before
    assert list(incoming.trail) == trail_before
    assert [(e.position, e.radius, e.elapsed) for e in game.explosions] == exp_state_before

