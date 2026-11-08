"""Tests for job 004-game-states: start screen, ESC pause/resume, SPACE restart, game-time spawns."""

import gc
import json
import random
import types

import pygame
import pytest

import systems.score
import utils.timer
from entities import IncomingMissile
from game.constants import (DT_DEFAULT, SCREEN_HEIGHT, STATE_GAME_OVER, STATE_PAUSED,
                            STATE_PLAYING, STATE_START)
from systems.game_loop import MainGame

Vector2 = pygame.math.Vector2
FIRE = {"fire_missile": (400, 300)}


@pytest.fixture
def game(main_game):
    """The shared ``main_game`` fixture, seeded and able to fire at once."""
    random.seed(0)
    main_game.base.cooldown_time = 0
    return main_game


@pytest.fixture
def fresh_game(monkeypatch, tmp_path):
    """Return a factory for a ``MainGame()`` on the start screen (no ``start_game()``)."""
    gc.collect()
    random.seed(0)
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))

    def make(high_score=None):
        if high_score is not None:
            (tmp_path / "config.json").write_text(json.dumps({"high_score": high_score}))
        new_game = MainGame()
        new_game.base.cooldown_time = 0
        return new_game

    yield make
    gc.collect()
    pygame.quit()


def _fake_events(monkeypatch, game, script, on_call=None):
    """Make ``handle_events`` return ``script[i]`` on call ``i + 1``; the last entry must quit."""
    assert script[-1] == {"quit": True}
    calls = [0]

    def fake():
        calls[0] += 1
        if on_call:
            on_call(calls[0])
        return script[calls[0] - 1]

    monkeypatch.setattr(game, "handle_events", fake)
    return calls


def _assert_fresh_city(game):
    """Assert a just-started game: playing, 8 full-health buildings, clocks at zero."""
    assert game.state == STATE_PLAYING and len(game.buildings) == 8
    assert all(b.health_current == b.health_max for b in game.buildings)
    assert game.game_time == 0.0 and game.last_spawn_time == 0.0


@pytest.mark.parametrize("event, expected", [
    (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), {"toggle_pause": True}),
    (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), {"start": True}),
    (pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)), FIRE),
])
def test_input_mapping(game, event, expected):
    """Criterion 1: ESC toggles pause, SPACE starts, a left click fires."""
    pygame.event.clear()
    pygame.event.post(event)
    assert game.input_system.handle_events() == expected


def test_opens_on_start_screen(fresh_game, monkeypatch):
    """Criterion 2: the real loop stays on the start screen with no forced game."""
    game = fresh_game()
    calls = _fake_events(monkeypatch, game, [{}] * 4 + [{"quit": True}])
    game.start_game_loop()
    assert calls[0] == 5 and game.state == STATE_START
    assert game.buildings == [] and game.incoming_missiles == []
    assert game.game_time == 0.0


def test_space_starts_play(fresh_game):
    """Criterion 3: SPACE on the start screen starts a fresh game."""
    game = fresh_game()
    game.handle_actions({"start": True})
    _assert_fresh_city(game)


@pytest.mark.parametrize("state, actions", [
    (STATE_START, {"toggle_pause": True}),
    (STATE_START, FIRE),
    (STATE_PAUSED, {"start": True}),
    (STATE_PAUSED, FIRE),
    (STATE_PLAYING, {"start": True}),
    (STATE_GAME_OVER, {"toggle_pause": True}),
])
def test_ignored_input(request, state, actions):
    """Criteria 4, 6, 7, 10: these inputs change nothing, keep the city and fire nothing."""
    if state == STATE_START:
        game = request.getfixturevalue("fresh_game")()
    else:
        game = request.getfixturevalue("game")
        game.state = state
    before = list(game.buildings)
    game.handle_actions(actions)
    assert game.state == state and game.defense_missiles == []
    assert len(game.buildings) == len(before)
    assert all(a is b for a, b in zip(game.buildings, before))


def test_pause_and_resume_keep_everything(game):
    """Criterion 5: ESC pauses, ESC resumes, and nothing in the game changes."""
    missile = IncomingMissile(Vector2(400, 500))
    missile.position, missile.velocity = Vector2(300, 200), Vector2(0, 0)
    game.incoming_missiles.append(missile)
    game.score_system.score, game.game_time = 77, 4.25

    def snapshot():
        return ([(id(b), b.health_current) for b in game.buildings], game.game_time,
                game.score_system.score, Vector2(missile.position))

    before = snapshot()
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PAUSED
    game.handle_actions({"toggle_pause": True})
    assert game.state == STATE_PLAYING and snapshot() == before


def test_firing_in_play(game):
    """Criterion 8: a click fires once in play; a click with ESC pauses and doesn't fire."""
    game.handle_actions(FIRE)
    assert len(game.defense_missiles) == 1
    game.defense_missiles, game.base.cooldown_time = [], 0
    game.handle_actions({"toggle_pause": True, **FIRE})
    assert game.state == STATE_PAUSED and game.defense_missiles == []


def test_space_restarts_from_game_over(game, monkeypatch):
    """Criterion 9: SPACE on game over starts a clean game without saving again."""
    game.score_system.score = 120
    saves = [0]
    real_save = game.score_system.save_high_score

    def counting_save():
        saves[0] += 1
        real_save()

    monkeypatch.setattr(game.score_system, "save_high_score", counting_save)
    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()
    assert game.state == STATE_GAME_OVER and saves[0] == 1

    game.handle_actions({"start": True})
    _assert_fresh_city(game)
    assert game.score_system.score == 0 and game.score_system.high_score == 120
    assert saves[0] == 1
    assert game.incoming_missiles == [] and game.defense_missiles == [] and game.explosions == []
    game.check_game_over()
    assert game.state == STATE_PLAYING


def test_spawns_run_on_game_time(game, monkeypatch):
    """Criterion 11: the first spawn comes at t ~= 3.32 s of game time; no get_ticks."""
    def no_ticks():
        raise AssertionError("pygame.time.get_ticks must not be called")

    monkeypatch.setattr(pygame.time, "get_ticks", no_ticks)
    game.last_spawn_time = 0.0
    for _ in range(180):
        game.update(DT_DEFAULT)
    assert game.incoming_missiles == []
    for _ in range(30):
        game.update(DT_DEFAULT)
    assert len(game.incoming_missiles) == 1
    assert game.last_spawn_time == pytest.approx(3.32, abs=0.02)


def test_pause_does_not_advance_game_time(game, monkeypatch):
    """Criterion 12: 60 s spent paused adds no game time and spawns nothing."""
    clock = [1000.0]
    monkeypatch.setattr(utils.timer, "time", types.SimpleNamespace(time=lambda: clock[0]))
    game.timer.reset()
    game.last_spawn_time = 0.0
    script = ([{}] * 30 + [{"toggle_pause": True}, {}, {"toggle_pause": True}]
              + [{}] * 7 + [{"quit": True}])

    def tick(call):
        if call < len(script):
            clock[0] += 1 / 60 + (60 if call == 32 else 0)

    calls = _fake_events(monkeypatch, game, script, on_call=tick)
    game.start_game_loop()
    assert calls[0] == 41 and game.state == STATE_PLAYING
    assert game.game_time == pytest.approx(37 / 60, abs=1e-6)
    assert game.incoming_missiles == []


def _check_menu(game, expected):
    """Assert ``expected`` texts appear and lines run down the screen >= 30 px apart."""
    lines = game.menu_lines()
    texts = [line[0] for line in lines]
    ys = [line[3] for line in lines]
    assert set(expected) <= set(texts)
    assert not any("Start/Pause" in text for text in texts)
    assert all(b - a >= 30 for a, b in zip(ys, ys[1:]))
    assert all(0 <= y <= SCREEN_HEIGHT for y in ys)
    game.draw_start_screen()


def test_menu_text(fresh_game):
    """Criterion 13: start and pause text, layout, and every menu screen draws."""
    game = fresh_game(high_score=250)
    _check_menu(game, ["High Score: 250", "Press SPACE to Start"])
    game.state, game.score_system.score = STATE_PAUSED, 1234
    _check_menu(game, ["PAUSED", "Score: 1,234", "Press ESC to Resume"])
    game.state = STATE_GAME_OVER
    game.draw_start_screen()
