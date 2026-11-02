"""Tests for job 003-buildings-game-over.

Only enemy missile impacts damage buildings (three hits destroy one),
destroyed buildings leave the city, the game ends once when the last
building falls, and ``ScoreSystem.save_high_score()`` is safe on any file.
"""

import json
import random

import pygame
import pytest

import systems.score
from entities import Building, IncomingMissile
from game.constants import (
    COLOR_GRAY,
    DT_DEFAULT,
    SCREEN_SHAKE_BUILDING_HIT,
    STATE_GAME_OVER,
    STATE_PAUSED,
    STATE_PLAYING,
)
from systems.score import ScoreSystem

Vector2 = pygame.math.Vector2


@pytest.fixture
def game(main_game):
    """The shared ``main_game`` fixture with ``random`` seeded to 0."""
    random.seed(0)
    return main_game


def _centre(building):
    """Return the centre point of ``building``."""
    return building.position + Vector2(building.width / 2, building.height / 2)


def _impact(game, building, point=None):
    """Park a stationary enemy missile at ``point`` (default: ``building``'s centre), then collide."""
    missile = IncomingMissile(Vector2(building.position))
    missile.position = Vector2(point if point is not None else _centre(building))
    missile.velocity = Vector2(0, 0)
    game.incoming_missiles.append(missile)
    game.check_collisions()
    return missile


def _destroy_by_impacts(game, buildings):
    """Hit each of ``buildings`` three times through the game."""
    for building in list(buildings):
        for _ in range(3):
            _impact(game, building)


def _frames(game, n, collide=True):
    """Run ``n`` frames of ``update`` (and ``check_collisions`` if ``collide``)."""
    for _ in range(n):
        game.update(DT_DEFAULT)
        if collide:
            game.check_collisions()


def _count_saves(game, monkeypatch):
    """Wrap ``save_high_score`` with a counter; return the one-item count list."""
    count = [0]
    real_save = game.score_system.save_high_score

    def counting_save():
        count[0] += 1
        real_save()

    monkeypatch.setattr(game.score_system, "save_high_score", counting_save)
    return count


def _mark_all_destroyed(game):
    """Set ``is_destroyed`` on every building without filtering the list."""
    for building in game.buildings:
        building.is_destroyed = True


# --- Criteria 1-9: building damage --------------------------------------------

def test_three_impacts_destroy_a_building():
    """Criterion 1: 100 -> 66 -> 32 -> 0, destroyed on the third impact."""
    building = Building(30, 540)
    assert building.health_current == 100
    for expected in (66, 32):
        building.take_impact()
        assert building.health_current == expected
    assert building.is_destroyed is False
    building.take_impact()
    assert building.health_current == 0
    assert building.is_destroyed is True


def test_impact_through_the_game(game):
    """Criteria 2 and 3: one impact costs 34 health; its explosion adds nothing."""
    missile = _impact(game, game.buildings[0])
    assert missile.is_destroyed
    assert [b.health_current for b in game.buildings] == [66] + [100] * 7
    assert game.shake_intensity == SCREEN_SHAKE_BUILDING_HIT
    assert len(game.explosions) == 1
    assert game.explosions[0].is_player is False

    _frames(game, 60)
    assert game.buildings[0].health_current == 66


def test_player_explosions_never_damage_buildings(game):
    """Criterion 4: player explosions over the city leave every building whole."""
    b0, b1 = game.buildings[0], game.buildings[1]
    for point in (b0.position, _centre(b0), _centre(b1)):
        game.explosions.append(
            game.explosion_pool.get_explosion(point.x, point.y, is_player=True))
    _frames(game, 60)
    assert all(b.health_current == b.health_max for b in game.buildings)
    assert len(game.buildings) == 8
    assert game.buildings_left == 8


def test_one_missile_damages_one_building(game):
    """Criterion 5: overlapping buildings share one impact, not two."""
    b0, b1 = game.buildings[0], game.buildings[1]
    b1.position = Vector2(b0.position)
    _impact(game, b0)
    assert sorted([b0.health_current, b1.health_current]) == [66, 100]


def test_destroyed_buildings_leave_the_list(game):
    """Criterion 6: a destroyed building is filtered out and can't be hit again."""
    b0 = game.buildings[0]
    old_centre = _centre(b0)
    _destroy_by_impacts(game, [b0])
    assert b0.is_destroyed
    assert b0 not in game.buildings
    assert len(game.buildings) == 7
    assert game.buildings_left == 7

    explosions_before = len(game.explosions)
    stray = _impact(game, b0, old_centre)
    assert stray.is_destroyed is False
    assert len(game.explosions) == explosions_before


def test_buildings_left_counts_standing_buildings(game):
    """Criterion 7: ``buildings_left`` counts ``is_destroyed``, not list length."""
    game.buildings[0].is_destroyed = True
    game.buildings[3].is_destroyed = True
    assert game.buildings_left == 6
    assert len(game.buildings) == 8


def test_spawns_target_standing_buildings_only(game):
    """Criterion 8: only the last standing building is ever targeted."""
    for building in game.buildings[:7]:
        building.is_destroyed = True
    for _ in range(20):
        game.spawn_incoming_missile()
    assert len(game.incoming_missiles) == 20
    target_x = game.buildings[7].position.x
    assert target_x == 590
    assert all(m.target.x == target_x for m in game.incoming_missiles)


def test_city_redraws_without_destroyed_building(game):
    """Criterion 9: the destroyed building's pixels are no longer drawn."""
    game.draw()
    assert game.screen.get_at((60, 560))[:3] == COLOR_GRAY
    _destroy_by_impacts(game, [game.buildings[0]])
    _frames(game, 60, collide=False)
    game.draw()
    assert game.screen.get_at((60, 560))[:3] != COLOR_GRAY


# --- Criteria 10-14: game over ------------------------------------------------

def test_game_over_when_last_building_falls(game, monkeypatch, tmp_path):
    """Criteria 10 and 11: no game over until the last building falls, then save once."""
    saves = _count_saves(game, monkeypatch)
    _destroy_by_impacts(game, game.buildings[:7])
    game.check_game_over()
    assert game.state == STATE_PLAYING
    assert saves[0] == 0

    game.score_system.score = 120
    _destroy_by_impacts(game, game.buildings)
    game.check_game_over()
    assert game.state == STATE_GAME_OVER
    assert game.buildings_left == 0
    assert saves[0] == 1
    config_file = tmp_path / "config.json"
    assert json.loads(config_file.read_text()) == {"high_score": 120}
    assert game.score_system.high_score == 120


def test_game_over_saves_exactly_once(game, monkeypatch):
    """Criterion 12: repeated checks after game over don't save again."""
    saves = _count_saves(game, monkeypatch)
    _mark_all_destroyed(game)
    game.check_collisions()
    for _ in range(5):
        game.check_game_over()
    assert game.state == STATE_GAME_OVER
    assert saves[0] == 1


def test_no_game_over_outside_play(game, monkeypatch):
    """Criterion 13: a fallen city while paused doesn't end the game."""
    saves = _count_saves(game, monkeypatch)
    game.state = STATE_PAUSED
    _mark_all_destroyed(game)
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_PAUSED
    assert saves[0] == 0


def test_real_loop_ends_game_and_saves_once(game, monkeypatch):
    """Criterion 14: ``start_game_loop()`` reaches game over and saves once."""
    saves = _count_saves(game, monkeypatch)
    calls = [0]

    def fake_handle_events():
        calls[0] += 1
        if calls[0] == 1:
            _mark_all_destroyed(game)
        return {"quit": True} if calls[0] >= 10 else {}

    monkeypatch.setattr(game, "handle_events", fake_handle_events)
    game.start_game_loop()
    assert calls[0] == 10
    assert game.state == STATE_GAME_OVER
    assert saves[0] == 1


# --- Criterion 15: save_high_score file handling ------------------------------

REAL_CONFIG_KEYS = {
    "high_score": 50,
    "sound_enabled": True,
    "difficulty_multiplier": 1.0,
    "spawn_rate_modifier": 1.0,
    "fullscreen": False,
    "last_session": None,
}


def _score_system(monkeypatch, path, score, contents=None):
    """Point ``CONFIG_PATH`` at missing ``path``, build a ScoreSystem, then write ``contents``.

    The file is written after construction so these tests exercise only
    ``save_high_score()``; ``load_high_score()`` is covered by
    ``tests/test_load_high_score.py``.
    """
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(path))
    score_system = ScoreSystem()
    score_system.score = score
    if contents is not None:
        path.write_text(contents)
    return score_system


def _save_and_check_high_score(score_system):
    """Save, then assert the in-memory high score is max(previous, score)."""
    expected = max(score_system.high_score, score_system.score)
    score_system.save_high_score()
    assert score_system.high_score == expected


def test_save_keeps_other_keys(monkeypatch, tmp_path):
    """Criterion 15a: a new high is written and unknown keys are kept."""
    path = tmp_path / "config.json"
    score_system = _score_system(monkeypatch, path, 120, json.dumps(REAL_CONFIG_KEYS))
    _save_and_check_high_score(score_system)
    assert json.loads(path.read_text()) == {**REAL_CONFIG_KEYS, "high_score": 120}


@pytest.mark.parametrize("contents", [
    json.dumps({"high_score": 200}),
    "{not json",
    "[1, 2]",
    '{"high_score": "abc"}',
    '{"high_score": 1e999}',
    '{"high_score": Infinity}',
    pytest.param("[" * 200_000, id="deeply-nested"),
])
def test_save_leaves_file_untouched(monkeypatch, tmp_path, contents):
    """Criteria 15b and 15c: a lower score or an unreadable file changes nothing."""
    path = tmp_path / "config.json"
    score_system = _score_system(monkeypatch, path, 120, contents)
    before = path.read_bytes()
    _save_and_check_high_score(score_system)
    assert path.read_bytes() == before


def test_save_to_directory_does_not_raise(monkeypatch, tmp_path):
    """Criterion 15d: an unwritable ``CONFIG_PATH`` never raises."""
    path = tmp_path / "config.json"
    score_system = _score_system(monkeypatch, path, 120)
    path.mkdir()
    _save_and_check_high_score(score_system)
    assert path.is_dir()


def test_save_zero_score_creates_no_file(monkeypatch, tmp_path):
    """Criterion 15e: a missing file and a zero score create nothing."""
    path = tmp_path / "config.json"
    score_system = _score_system(monkeypatch, path, 0)
    _save_and_check_high_score(score_system)
    assert not path.exists()


# --- Criterion 16: game-over screen -------------------------------------------

def test_game_over_screen_draws(game):
    """Criterion 16: the game-over screen renders without raising."""
    game.state = STATE_GAME_OVER
    game.draw_start_screen()
