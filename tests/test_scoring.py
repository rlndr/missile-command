"""Tests for job 006-scoring: intercept points, survival bonus and the live HUD score.

A player explosion that destroys an enemy missile scores
``MISSILE_INTERCEPT_POINTS`` once; every whole second survived in play scores
``SURVIVAL_POINTS_PER_SECOND``; the HUD shows the live score right-aligned.
"""

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
def fresh_scores(monkeypatch, tmp_path):
    """Return a factory for bare ``ScoreSystem()`` objects reading a ``tmp_path`` config."""
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    return ScoreSystem


def _park(game, x, y):
    """Add an ``IncomingMissile`` parked at ``(x, y)`` with zero velocity; return it."""
    missile = IncomingMissile(Vector2(x, 500))
    missile.position = Vector2(x, y)
    missile.velocity = Vector2(0, 0)
    game.incoming_missiles.append(missile)
    return missile


def _blast(game, x=400, y=300, is_player=True):
    """Add an explosion at ``(x, y)`` advanced to radius 40; return it."""
    explosion = game.explosion_pool.get_explosion(x, y, is_player=is_player)
    game.explosions.append(explosion)
    explosion.update(0.25)
    assert explosion.radius == pytest.approx(40)
    return explosion


def _centre(building):
    """Return the centre point of ``building``'s collision box."""
    return building.position + Vector2(building.width / 2, building.height / 2)


def _intercept_one(game):
    """Criterion 1 setup: one player blast and one missile inside it, then collide."""
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


def _run_loop_with_fake_clock(game, monkeypatch, frames, step):
    """Run ``start_game_loop()`` for ``frames`` empty frames, each advancing a fake clock by ``step`` s."""
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


def _region(screen, rect):
    """Return the RGB values of every pixel in ``rect`` as a list."""
    x0, y0, w, h = rect
    return [tuple(screen.get_at((x, y)))[:3]
            for y in range(y0, y0 + h) for x in range(x0, x0 + w)]


# --- Criteria 1-4: intercept points ----------------------------------------


def test_one_intercept_scores_once(game):
    """Criterion 1: one intercept gives 10 points and 1 hit, and never again."""
    missile = _intercept_one(game)
    assert missile.is_destroyed
    assert game.score_system.score == MISSILE_INTERCEPT_POINTS == 10
    assert game.score_system.total_missiles_hit == 1
    for _ in range(4):
        game.check_collisions()
    assert game.score_system.score == 10
    assert game.score_system.total_missiles_hit == 1


def test_several_intercepts_in_one_blast(game):
    """Criterion 2: three missiles inside one blast score three times; the outside one survives."""
    _blast(game)
    inside = [_park(game, 400, 300), _park(game, 430, 300), _park(game, 400, 335)]
    outside = _park(game, 450, 300)
    game.check_collisions()
    assert all(m.is_destroyed for m in inside)
    assert not outside.is_destroyed
    assert game.score_system.score == 3 * MISSILE_INTERCEPT_POINTS
    assert game.score_system.total_missiles_hit == 3


def test_overlapping_blasts_count_once(game):
    """Criterion 3: a missile inside two player blasts scores once."""
    _blast(game, 400, 300)
    _blast(game, 420, 300)
    _park(game, 410, 300)
    game.check_collisions()
    assert game.score_system.score == 10
    assert game.score_system.total_missiles_hit == 1


def _non_player_blast(game):
    """A non-player explosion around a parked missile."""
    _blast(game, 400, 300, is_player=False)
    missile = _park(game, 410, 300)
    game.check_collisions()
    assert not missile.is_destroyed


def _building_impact(game):
    """A parked missile at a building's centre."""
    building = game.buildings[0]
    missile = _park(game, *_centre(building))
    game.check_collisions()
    assert missile.is_destroyed and building.health_current == 66


def _impact_inside_player_blast(game):
    """A missile at a building's centre that is also inside a player blast."""
    building = game.buildings[0]
    centre = _centre(building)
    _blast(game, centre.x, centre.y)
    missile = _park(game, centre.x, centre.y)
    game.check_collisions()
    assert missile.is_destroyed and building.health_current == 66


def _off_screen(game):
    """A missile below the bottom of the screen is filtered out."""
    missile = _park(game, 400, SCREEN_HEIGHT + 60)
    game.update(DT_DEFAULT)
    game.check_collisions()
    assert missile not in game.incoming_missiles


@pytest.mark.parametrize("case", [_non_player_blast, _building_impact,
                                  _impact_inside_player_blast, _off_screen],
                         ids=["non_player_blast", "building_impact",
                              "impact_inside_player_blast", "off_screen"])
def test_no_points_for_other_deaths(game, case):
    """Criterion 4: missiles that die any other way score nothing."""
    assert game.score_system.score == 0
    case(game)
    assert game.score_system.score == 0
    assert game.score_system.total_missiles_hit == 0


# --- Criteria 5-9: survival time -------------------------------------------


@pytest.mark.parametrize("calls, expected", [(59, 0), (61, 1)])
def test_survival_accumulates_first_second(fresh_scores, calls, expected):
    """Criterion 5: fractional frames add up to a point after one whole second."""
    scores = fresh_scores()
    for n in range(1, calls + 1):
        scores.add_survival_time(DT_DEFAULT)
        if n == 59:
            assert scores.score == 0
    assert scores.score == expected
    assert scores.time_survived == pytest.approx(calls * DT_DEFAULT)


def test_survival_accumulates_over_a_minute(fresh_scores):
    """Criterion 5: 3599 frames give 59 points and 3601 give 60."""
    scores = fresh_scores()
    for _ in range(3599):
        scores.add_survival_time(DT_DEFAULT)
    assert scores.score == 59
    assert scores.time_survived == pytest.approx(3599 * DT_DEFAULT)
    for _ in range(2):
        scores.add_survival_time(DT_DEFAULT)
    assert scores.score == 60
    assert scores.time_survived == pytest.approx(3601 * DT_DEFAULT)


def test_survival_large_and_uneven_dt(fresh_scores):
    """Criterion 6: exact values for quarter, multi-second and half-second steps."""
    scores = fresh_scores()
    for _ in range(3):
        scores.add_survival_time(0.25)
    assert scores.score == 0
    scores.add_survival_time(0.25)
    assert scores.score == 1
    scores.add_survival_time(2.5)
    assert scores.score == 3
    scores.add_survival_time(0.5)
    assert scores.score == 4
    assert scores.time_survived == 4.0


def test_survival_ignores_non_positive_dt(fresh_scores):
    """Criterion 7: zero and negative dt change nothing."""
    scores = fresh_scores()
    assert scores.time_survived == 0.0 and isinstance(scores.time_survived, float)
    scores.add_survival_time(0.75)
    assert scores.time_survived == 0.75 and scores.score == 0
    scores.add_survival_time(0.0)
    scores.add_survival_time(-1.0)
    assert scores.time_survived == 0.75 and scores.score == 0


def test_survival_through_the_game(game):
    """Criterion 8: 121 frames of play score 2, matching whole seconds of game time."""
    for _ in range(121):
        game.update(DT_DEFAULT)
    assert game.score_system.score == 2
    assert game.score_system.score == int(game.game_time)
    assert game.score_system.total_missiles_hit == 0


def test_paused_does_not_score(game, monkeypatch):
    """Criterion 9: 10 s spent paused adds no score and no survival time."""
    game.state = STATE_PAUSED
    _run_loop_with_fake_clock(game, monkeypatch, frames=10, step=1.0)
    assert game.score_system.score == 0
    assert game.score_system.time_survived == 0.0


def test_game_over_does_not_score(game, monkeypatch):
    """Criterion 9: 10 s on the game-over screen leaves a score of 50 alone."""
    game.state = STATE_GAME_OVER
    game.score_system.score = 50
    _run_loop_with_fake_clock(game, monkeypatch, frames=10, step=1.0)
    assert game.score_system.score == 50
    assert game.score_system.time_survived == 0.0


# --- Criteria 10-11: restart and high score --------------------------------


def test_restart_resets_scoring(game):
    """Criterion 10: SPACE after game over zeroes score, hits and survival time."""
    _intercept_one(game)
    game.score_system.add_survival_time(0.75)
    assert game.score_system.score == 10 and game.score_system.total_missiles_hit == 1
    _end_game(game)
    assert game.state == STATE_GAME_OVER
    game.handle_actions({"start": True})
    assert game.score_system.score == 0
    assert game.score_system.total_missiles_hit == 0
    assert game.score_system.time_survived == 0.0
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


# --- Criteria 12-14: HUD and dead code -------------------------------------


def test_hud_text_is_live(game):
    """Criterion 12: the HUD text follows the score, with thousands separators."""
    hud_rect = (SCREEN_WIDTH - 300, 0, 300, 50)
    assert game.hud_score_text() == "SCORE: 0"
    game.draw()
    before = _region(game.screen, hud_rect)
    _intercept_one(game)
    assert game.hud_score_text() == "SCORE: 10"
    game.draw()
    assert _region(game.screen, hud_rect) != before
    game.score_system.score = 1234567
    assert game.hud_score_text() == "SCORE: 1,234,567"


def test_hud_right_aligned_and_on_screen(game):
    """Criterion 13: the largest score draws in yellow and stays out of the right margin."""
    game.score_system.score = HIGH_SCORE_MAX
    game.draw()
    text_area = _region(game.screen, (SCREEN_WIDTH - 300, 10,
                                      300 - HUD_MARGIN, 36))
    assert COLOR_YELLOW in text_area
    margin = _region(game.screen, (SCREEN_WIDTH - HUD_MARGIN, 0, HUD_MARGIN, 50))
    assert all(red == COLOR_BLUE[0] for red, _, _ in margin)


def test_dead_score_code_removed():
    """Criterion 14: handle_score_updates, get_ticks and the unused counter are gone."""
    source = inspect.getsource(systems.game_loop)
    assert not hasattr(MainGame, "handle_score_updates")
    assert "get_ticks" not in source
    assert "total_missile_hits_this_level" not in source
