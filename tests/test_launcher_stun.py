"""Tests for the launcher stun on a direct hit (job 004).

An enemy missile that hits the launcher body is destroyed with an ordinary
enemy explosion and the impact sound, and knocks the launcher offline for
``LAUNCHER_STUN_DURATION`` seconds. A hit while stunned restarts the stun.
"""

import pygame

from entities import IncomingMissile
from game.constants import (GROUND_Y, LAUNCHER_HEIGHT, LAUNCHER_STUN_DURATION,
                            LAUNCHER_X, STATE_PAUSED, STATE_PLAYING)

Vector2 = pygame.math.Vector2

HIT_POINT = (LAUNCHER_X, GROUND_Y - LAUNCHER_HEIGHT // 2)


def spy(monkeypatch, game):
    """Replace ``game.sound.play`` with a recorder and return its call list."""
    calls = []
    monkeypatch.setattr(game.sound, "play", lambda n: calls.append(n) or True)
    return calls


def park_missile(game, x, y):
    """Add a stationary ``IncomingMissile`` at ``(x, y)`` to ``game`` and return it."""
    missile = IncomingMissile(Vector2(x, y))
    missile.position = Vector2(x, y)
    missile.velocity = Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def hit_launcher(game):
    """Park a missile inside the launcher body and run ``check_collisions()``."""
    missile = park_missile(game, *HIT_POINT)
    game.check_collisions()
    return missile


def test_direct_hit_destroys_missile_and_stuns(main_game, monkeypatch):
    game = main_game
    calls = spy(monkeypatch, game)
    assert game.base.get_bounds().collidepoint(HIT_POINT)
    before = list(game.explosions)

    missile = hit_launcher(game)

    assert missile.is_destroyed is True
    added = [e for e in game.explosions if e not in before]
    assert len(game.explosions) == len(before) + 1
    assert len(added) == 1
    explosion = added[0]
    assert explosion.is_player is False
    assert explosion.is_building is False
    assert explosion.position == missile.position
    assert game.base.is_active is False
    assert game.base.stun_time == LAUNCHER_STUN_DURATION
    assert game.base.can_fire() is False
    assert calls.count("impact") == 1


def test_comes_back_online_after_duration(main_game):
    game = main_game
    hit_launcher(game)
    game.base.update(LAUNCHER_STUN_DURATION - 0.01)
    assert game.base.is_active is False
    game.base.update(0.02)
    assert game.base.is_active is True
    assert game.base.stun_time == 0.0


def test_single_full_update_brings_it_back(main_game):
    game = main_game
    game.base.stun()
    game.base.update(LAUNCHER_STUN_DURATION)
    assert game.base.is_active is True
    assert game.base.stun_time == 0.0


def test_repeat_hit_restarts_stun(main_game):
    game = main_game
    hit_launcher(game)
    game.base.update(2.0)
    hit_launcher(game)
    assert game.base.stun_time == LAUNCHER_STUN_DURATION
    game.base.update(LAUNCHER_STUN_DURATION - 0.01)
    assert game.base.is_active is False
    game.base.update(0.02)
    assert game.base.is_active is True


def test_firing_blocked_while_stunned(main_game, monkeypatch):
    game = main_game
    calls = spy(monkeypatch, game)
    game.base.cooldown_time = 0.0
    game.base.stun()
    count = len(game.defense_missiles)
    game.handle_actions({"fire_missile": (400, 300)})
    assert len(game.defense_missiles) == count
    assert "launch" not in calls
    assert "laser" not in calls


def test_reload_frozen_then_resumes(main_game):
    game = main_game
    game.base.cooldown_time = 1.0
    game.base.stun()
    game.base.update(1.0)
    assert game.base.cooldown_time == 1.0
    game.base.update(LAUNCHER_STUN_DURATION)
    assert game.base.is_active is True
    assert game.base.cooldown_time == 1.0
    game.base.update(0.5)
    assert game.base.cooldown_time == 0.5


def test_pause_does_not_advance_stun(main_game):
    game = main_game
    hit_launcher(game)
    game.update(0.5)
    stun_left = game.base.stun_time
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    for _ in range(600):
        game.handle_actions({})
    assert game.base.stun_time == stun_left
    assert game.base.is_active is False
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING
    assert game.base.stun_time == stun_left


def test_reset_clears_stun(main_game):
    game = main_game
    game.base.stun()
    game.base.reset()
    assert game.base.is_active is True
    assert game.base.stun_time == 0.0
    assert game.base.can_fire() is True


def test_start_game_clears_stun(main_game):
    game = main_game
    game.base.stun()
    game.start_game()
    assert game.base.is_active is True
    assert game.base.stun_time == 0.0
    assert game.base.can_fire() is True


def test_hit_leaves_score_and_buildings(main_game):
    game = main_game
    score = game.score_system.score
    buildings = list(game.buildings)
    health = [(b.health_current, b.is_destroyed) for b in game.buildings]

    hit_launcher(game)

    assert game.base.is_active is False
    assert game.score_system.score == score
    assert game.buildings == buildings
    assert [(b.health_current, b.is_destroyed) for b in game.buildings] == health
    game.check_game_over()
    assert game.state == STATE_PLAYING
