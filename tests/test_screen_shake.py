"""Regression and harness tests for building hit, intercept, and headless display."""

import os
import random
from pathlib import Path

import pygame

import systems.score
from entities import IncomingMissile
from game.constants import DT_DEFAULT


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
    """Building hit, then 10 frames of update/check_collisions/draw."""
    random.seed(0)
    game = main_game
    missile = _place_missile_on_building(game)

    # Frame 1: the hit.
    game.update(DT_DEFAULT)
    game.check_collisions()
    assert missile.is_destroyed is True
    game.draw()

    # Frames 2-10.
    for _ in range(9):
        _frame(game)


def test_intercept_and_next_frame_draws(main_game):
    """An intercept destroys the incoming missile and the next frame draws cleanly."""
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

    game.update(DT_DEFAULT)
    game.draw()


def test_harness_isolates_config_and_display(main_game, tmp_path):
    """Config path is under tmp_path and SDL runs headless."""
    config_path = Path(systems.score.CONFIG_PATH).resolve()
    assert config_path.is_relative_to(tmp_path.resolve())
    assert os.environ["SDL_VIDEODRIVER"] == "dummy"
    assert os.environ["SDL_AUDIODRIVER"] == "dummy"
