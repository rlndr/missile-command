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
from game.constants import (
    DT_DEFAULT,
    SCREEN_SHAKE_BUILDING_HIT,
    SCREEN_SHAKE_DECAY_RATE,
    SCREEN_SHAKE_INTERCEPT,
)


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
    """Criterion 7: an intercept sets intercept shake and the next frame survives."""
    random.seed(0)
    game = main_game
    game.incoming_missiles = []
    game.defense_missiles = []

    incoming = IncomingMissile(pygame.math.Vector2(400, 300))
    incoming.position = pygame.math.Vector2(400, 200)
    game.incoming_missiles.append(incoming)

    defence = DefenseMissile(pygame.math.Vector2(408, 208))
    defence.position = pygame.math.Vector2(408, 208)
    game.defense_missiles.append(defence)

    game.check_collisions()
    assert incoming.is_destroyed is True
    assert defence.is_destroyed is True
    assert game.shake_intensity == SCREEN_SHAKE_INTERCEPT

    game.update(DT_DEFAULT)
    assert game.shake_intensity != int(game.shake_intensity)
    game.draw()


def test_harness_isolates_config_and_display(main_game, tmp_path):
    """Criterion 8: config path is under tmp_path and SDL runs headless."""
    config_path = Path(systems.score.CONFIG_PATH).resolve()
    assert config_path.is_relative_to(tmp_path.resolve())
    assert os.environ["SDL_VIDEODRIVER"] == "dummy"
    assert os.environ["SDL_AUDIODRIVER"] == "dummy"
