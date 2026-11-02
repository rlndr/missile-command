"""Tests for job 006-scoring: intercept points, survival bonus and the live HUD score."""

import inspect
import json
import random
import types

import pygame
import pytest

import systems.game_loop
import systems.score
import utils.timer
from entities import IncomingMissile
from game.constants import (COLOR_BLUE, COLOR_YELLOW, DT_DEFAULT, HIGH_SCORE_MAX,
                            HUD_MARGIN, MISSILE_INTERCEPT_POINTS, SCREEN_HEIGHT,
                            SCREEN_WIDTH, STATE_GAME_OVER, STATE_PAUSED)
from systems.game_loop import MainGame
from systems.score import ScoreSystem

Vector2 = pygame.math.Vector2


@pytest.fixture
def game(main_game):
    """The shared ``main_game`` fixture with ``random`` seeded."""
    random.seed(0)
    return main_game


@pytest.fixture
def scores(monkeypatch, tmp_path):
    """A bare ``ScoreSystem()`` reading a config under ``tmp_path``."""
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    return ScoreSystem()


def _park(game, x, y):
    """Add an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity; return it."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position, missile.velocity = Vector2(x, y), Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def _blast(game, x=400, y=300, is_player=True):
    """Add an explosion at ``(x, y)`` advanced to radius 40."""
    explosion = game.explosion_pool.get_explosion(x, y, is_player=is_player)
    game.explosions.append(explosion)
    explosion.update(0.25)
    assert explosion.radius == pytest.approx(40)


def _centre(building):
    """Return the centre of ``building``'s collision box."""
    return building.position + Vector2(building.width / 2, building.height / 2)


def _intercept_one(game):
    """Criterion 1 setup: one player blast, one missile at (410, 300), then collide."""
    _blast(game)
    missile = _park(game, 410, 300)
    game.check_collisions()
    return missile


def _end_game(game):
    """Destroy every building and run the game-over check."""
    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()


def _loop_with_fake_clock(game, monkeypatch, frames=10, step=1.0):
    """Run ``start_game_loop()`` for ``frames`` empty frames, each advancing a fake clock by ``step``."""
    clock = [1000.0]
    monkeypatch.setattr(utils.timer, "time", types.SimpleNamespace(time=lambda: clock[0]))
    game.timer.reset()
    calls = [0]

    def fake_events():
        calls[0] += 1
        if calls[0] > frames:
            return {"quit": True}
        clock[0] += step
        return {}

    monkeypatch.setattr(game, "handle_events", fake_events)
    game.start_game_loop()
    assert calls[0] == frames + 1


def _region(screen, x0, y0, w, h):
    """Return the RGB of every pixel in the rect ``(x0, y0, w, h)``."""
    return [tuple(screen.get_at((x, y)))[:3]
            for y in range(y0, y0 + h) for x in range(x0, x0 + w)]


def _hits(game):
    """Return ``(score, total_missiles_hit)``."""
    return game.score_system.score, game.score_system.total_missiles_hit


def test_one_intercept_scores_once(game):
    """Criterion 1: one intercept gives 10 points and 1 hit, and never again."""
    assert _intercept_one(game).is_destroyed
    assert _hits(game) == (MISSILE_INTERCEPT_POINTS, 1) == (10, 1)
    for _ in range(4):
        game.check_collisions()
    assert _hits(game) == (10, 1)


def test_several_intercepts_in_one_blast(game):
    """Criterion 2: three missiles inside one blast score three times; the outside one survives."""
    _blast(game)
    inside = [_park(game, 400, 300), _park(game, 430, 300), _park(game, 400, 335)]
    outside = _park(game, 450, 300)
    game.check_collisions()
    assert all(m.is_destroyed for m in inside) and not outside.is_destroyed
    assert _hits(game) == (3 * MISSILE_INTERCEPT_POINTS, 3)


def test_overlapping_blasts_count_once(game):
    """Criterion 3: a missile inside two player blasts scores once."""
    _blast(game, 400, 300)
    _blast(game, 420, 300)
    _park(game, 410, 300)
    game.check_collisions()
    assert _hits(game) == (10, 1)


def _non_player_blast(game):
    """A non-player blast around a parked missile."""
    _blast(game, is_player=False)
    _park(game, 410, 300)


def _building_impact(game):
    """A parked missile at the centre of ``buildings[0]``."""
    _park(game, *_centre(game.buildings[0]))


def _impact_inside_player_blast(game):
    """A parked missile at the centre of ``buildings[0]``, inside a player blast."""
    centre = _centre(game.buildings[0])
    _blast(game, centre.x, centre.y)
    _park(game, centre.x, centre.y)


def _off_screen(game):
    """A missile below the screen, then one frame of play."""
    _park(game, 400, SCREEN_HEIGHT + 60)
    game.update(DT_DEFAULT)


@pytest.mark.parametrize("case, health, fate", [
    (_non_player_blast, 100, "alive"), (_building_impact, 66, "destroyed"),
    (_impact_inside_player_blast, 66, "destroyed"), (_off_screen, 100, "gone")])
def test_no_points_for_other_deaths(game, case, health, fate):
    """Criterion 4: missiles that die any other way (or survive a non-player blast) score nothing."""
    assert game.score_system.score == 0
    case(game)
    missiles = list(game.incoming_missiles)
    game.check_collisions()
    assert _hits(game) == (0, 0)
    assert game.buildings[0].health_current == health
    if fate == "gone":
        assert missiles == [] and game.incoming_missiles == []
    else:
        assert missiles[0].is_destroyed == (fate == "destroyed")


@pytest.mark.parametrize("first, second", [(59, 0), (3599, 59)])
def test_survival_accumulates_across_frames(scores, first, second):
    """Criterion 5: fractional frames add up; points arrive only after each whole second."""
    for _ in range(first):
        scores.add_survival_time(DT_DEFAULT)
    assert scores.score == second
    assert scores.time_survived == pytest.approx(first * DT_DEFAULT)
    for _ in range(2):
        scores.add_survival_time(DT_DEFAULT)
    assert scores.score == second + 1
    assert scores.time_survived == pytest.approx((first + 2) * DT_DEFAULT)


def test_survival_large_and_uneven_dt(scores):
    """Criterion 6: exact values for quarter, multi-second and half-second steps."""
    for dt, expected in [(0.25, 0), (0.25, 0), (0.25, 0), (0.25, 1), (2.5, 3), (0.5, 4)]:
        scores.add_survival_time(dt)
        assert scores.score == expected
    assert scores.time_survived == 4.0


def test_survival_ignores_non_positive_dt(scores):
    """Criterion 7: zero and negative dt change nothing."""
    assert scores.time_survived == 0.0 and isinstance(scores.time_survived, float)
    scores.add_survival_time(0.75)
    for dt in (0.0, -1.0):
        scores.add_survival_time(dt)
        assert (scores.time_survived, scores.score) == (0.75, 0)


def test_survival_through_the_game(game):
    """Criterion 8: 121 frames of play score 2, matching whole seconds of game time."""
    for _ in range(121):
        game.update(DT_DEFAULT)
    assert _hits(game) == (2, 0)
    assert game.score_system.score == int(game.game_time)


@pytest.mark.parametrize("state, preset", [(STATE_PAUSED, 0), (STATE_GAME_OVER, 50)])
def test_menu_states_do_not_score(game, monkeypatch, state, preset):
    """Criterion 9: 10 s spent paused or on game over adds no score or survival time."""
    game.state, game.score_system.score = state, preset
    _loop_with_fake_clock(game, monkeypatch)
    assert game.score_system.score == preset
    assert game.score_system.time_survived == 0.0


def test_restart_resets_scoring(game):
    """Criterion 10: SPACE after game over zeroes score, hits and survival time."""
    _intercept_one(game)
    game.score_system.add_survival_time(0.75)
    assert _hits(game) == (10, 1)
    _end_game(game)
    assert game.state == STATE_GAME_OVER
    game.handle_actions({"start": True})
    assert _hits(game) == (0, 0) and game.score_system.time_survived == 0.0
    game.score_system.add_survival_time(0.5)
    assert game.score_system.score == 0


def test_high_score_includes_new_points(game):
    """Criterion 11: an intercept plus 2 s survived saves a high score of 12."""
    _intercept_one(game)
    for _ in range(4):
        game.update(0.5)
    assert game.score_system.score == 12
    _end_game(game)
    with open(systems.score.CONFIG_PATH) as f:
        assert json.load(f) == {"high_score": 12}
    assert game.score_system.high_score == 12


def test_hud_text_is_live(game):
    """Criterion 12: the HUD text and pixels follow the score."""
    hud = (SCREEN_WIDTH - 300, 0, 300, 50)
    assert game.hud_score_text() == "SCORE: 0"
    game.draw()
    before = _region(game.screen, *hud)
    _intercept_one(game)
    assert game.hud_score_text() == "SCORE: 10"
    game.draw()
    assert _region(game.screen, *hud) != before
    game.score_system.score = 1234567
    assert game.hud_score_text() == "SCORE: 1,234,567"


def test_hud_right_aligned_and_on_screen(game):
    """Criterion 13: the largest score draws in yellow and stays out of the right margin."""
    game.score_system.score = HIGH_SCORE_MAX
    game.draw()
    assert COLOR_YELLOW in _region(game.screen, SCREEN_WIDTH - 300, 10, 300 - HUD_MARGIN, 36)
    margin = _region(game.screen, SCREEN_WIDTH - HUD_MARGIN, 0, HUD_MARGIN, 50)
    assert all(red == COLOR_BLUE[0] for red, _, _ in margin)


def test_dead_score_code_removed():
    """Criterion 14: handle_score_updates, get_ticks and the unused counter are gone."""
    source = inspect.getsource(systems.game_loop)
    assert not hasattr(MainGame, "handle_score_updates")
    assert "get_ticks" not in source and "total_missile_hits_this_level" not in source
