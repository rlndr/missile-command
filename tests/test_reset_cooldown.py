"""Tests for job 007-reset-cooldown: the launcher is ready to fire at the start of every game."""

import gc
import inspect
import types

import pygame
import pytest

import systems.game_loop
import systems.score
import utils.timer
from entities import DefenseMissile, DefensiveBase
from game.constants import (BASE_COOLDOWN_TIME, DT_DEFAULT, LAUNCHER_X_OFFSET,
                            LAUNCHER_Y_OFFSET, STATE_GAME_OVER, STATE_PLAYING,
                            STATE_START)
from systems.game_loop import MainGame

Vector2 = pygame.math.Vector2
FIRE = {"fire_missile": (400, 300)}
START = {"start": True}
PAUSE = {"toggle_pause": True}


@pytest.fixture
def start_screen_game(monkeypatch, tmp_path):
    """Return a factory for a start-screen ``MainGame()``.

    ``CONFIG_PATH`` is patched before the game is built. The game is left in
    ``STATE_START`` with no ``start_game()`` call and its launcher cooldown
    untouched, so it starts at ``BASE_COOLDOWN_TIME``.
    """
    gc.collect()
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    yield MainGame
    gc.collect()
    pygame.quit()


def _run_loop(monkeypatch, game, script):
    """Run ``start_game_loop()`` on ``script`` with a fake clock.

    ``handle_events`` returns ``script[i]`` on call ``i + 1``, and the fake
    ``utils.timer.time`` clock advances ``1/60`` s on every call. The last
    entry must quit. Returns the number of ``handle_events`` calls.
    """
    assert script[-1] == {"quit": True}
    clock = [1000.0]
    monkeypatch.setattr(utils.timer, "time", types.SimpleNamespace(time=lambda: clock[0]))
    game.timer.reset()
    calls = [0]

    def fake_events():
        calls[0] += 1
        clock[0] += 1 / 60
        return script[calls[0] - 1]

    monkeypatch.setattr(game, "handle_events", fake_events)
    game.start_game_loop()
    return calls[0]


def _end_game(game):
    """Destroy every building and run the game-over check."""
    for building in game.buildings:
        building.is_destroyed = True
    game.check_collisions()
    game.check_game_over()


def test_first_click_of_first_game_fires(start_screen_game):
    """Criterion 1: the first click after SPACE on the start screen fires at once."""
    game = start_screen_game()
    assert game.state == STATE_START
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME

    game.handle_actions(START)
    assert game.state == STATE_PLAYING
    assert game.base.cooldown_time == 0.0
    assert game.base.can_fire() is True

    game.handle_actions(FIRE)
    assert len(game.defense_missiles) == 1
    assert game.base.cooldown_time == BASE_COOLDOWN_TIME


def test_first_click_after_restart_fires(start_screen_game):
    """Criterion 2: a cooldown left over from the last game does not carry into the next."""
    game = start_screen_game()
    game.handle_actions(START)
    game.last_spawn_time = float("inf")
    game.handle_actions(FIRE)
    game.update(0.3)
    assert game.base.cooldown_time == pytest.approx(BASE_COOLDOWN_TIME - 0.3)

    _end_game(game)
    assert game.state == STATE_GAME_OVER
    assert game.base.cooldown_time > 0

    game.handle_actions(START)
    assert game.base.cooldown_time == 0.0
    game.handle_actions(FIRE)
    assert len(game.defense_missiles) == 1


@pytest.mark.parametrize("leftover", [0.01, 0.75, BASE_COOLDOWN_TIME])
@pytest.mark.parametrize("from_state", [STATE_START, STATE_GAME_OVER])
def test_every_way_into_a_game_resets(start_screen_game, from_state, leftover):
    """Criterion 3: SPACE from START or GAME_OVER always leaves a ready launcher."""
    game = start_screen_game()
    game.state = from_state
    game.base.cooldown_time = leftover
    game.base.is_active = False

    game.handle_actions(START)
    assert game.state == STATE_PLAYING
    assert game.base.cooldown_time == 0.0
    assert game.base.cooldown_ratio == 0.0
    assert game.base.is_active is True
    assert game.base.can_fire() is True


def test_start_game_keeps_the_same_launcher(start_screen_game):
    """Criterion 4: ``start_game()`` resets ``self.base`` in place and leaves it where it was."""
    game = start_screen_game()
    base = game.base
    game.start_game()
    assert game.base is base
    assert base.position == Vector2(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)


def test_base_reset_on_its_own():
    """Criterion 5: ``DefensiveBase.reset()`` readies a mid-reload launcher and is idempotent."""
    base = DefensiveBase()
    base.start_cooldown()
    base.update(0.5)
    assert base.cooldown_time == pytest.approx(1.0)

    position = Vector2(base.position)
    size = (base.width, base.height, base.render_offset_x, base.render_offset_y)

    base.reset()
    assert base.cooldown_time == 0.0
    assert base.cooldown_ratio == 0.0
    assert base.can_fire() is True

    snapshot = (base.cooldown_time, base.cooldown_ratio, base.is_active,
                Vector2(base.position), base.width, base.height,
                base.render_offset_x, base.render_offset_y)
    base.reset()
    assert (base.cooldown_time, base.cooldown_ratio, base.is_active,
            Vector2(base.position), base.width, base.height,
            base.render_offset_x, base.render_offset_y) == snapshot
    assert base.position == position
    assert (base.width, base.height, base.render_offset_x, base.render_offset_y) == size


def test_cooldown_still_works_in_a_game(main_game, monkeypatch):
    """Criterion 6: one shot per 1.5 s reload, checked just under and just over.

    The first missile reaches (400, 300) after about 1.24 s and is filtered
    out of ``defense_missiles``, so launches are counted with a recording
    ``DefenseMissile`` rather than by the length of the live list.
    """
    launched = []

    class RecordingMissile(DefenseMissile):
        """``DefenseMissile`` that records every launch."""

        def __init__(self, target_point):
            super().__init__(target_point)
            launched.append(self)

    monkeypatch.setattr(systems.game_loop, "DefenseMissile", RecordingMissile)
    game = main_game

    game.handle_actions(FIRE)
    game.handle_actions(FIRE)
    assert len(launched) == 1 and len(game.defense_missiles) == 1

    for _ in range(89):
        game.update(DT_DEFAULT)
    game.handle_actions(FIRE)
    assert len(launched) == 1
    assert game.base.cooldown_time > 0

    for _ in range(2):
        game.update(DT_DEFAULT)
    game.handle_actions(FIRE)
    assert len(launched) == 2
    assert game.defense_missiles[-1] is launched[-1]
    assert game.incoming_missiles == []


def test_pause_does_not_reset_the_cooldown(start_screen_game):
    """Criterion 7: ESC twice keeps the reload, so it can't be used to skip it."""
    game = start_screen_game()
    game.handle_actions(START)
    game.last_spawn_time = float("inf")
    game.handle_actions(FIRE)
    game.update(0.5)

    game.handle_actions(PAUSE)
    game.handle_actions(PAUSE)
    assert game.state == STATE_PLAYING
    assert game.base.cooldown_time == pytest.approx(BASE_COOLDOWN_TIME - 0.5)

    game.handle_actions(FIRE)
    assert len(game.defense_missiles) == 1


def test_space_and_click_same_frame_do_not_fire(start_screen_game):
    """Criterion 8: the click in the SPACE frame is ignored, but the launcher is ready."""
    game = start_screen_game()
    game.handle_actions({**START, **FIRE})
    assert game.state == STATE_PLAYING
    assert game.defense_missiles == []
    assert game.base.cooldown_time == 0.0


def test_first_click_through_the_real_loop(start_screen_game, monkeypatch):
    """Criterion 9: SPACE then a click one frame later fires through ``start_game_loop()``."""
    game = start_screen_game()
    calls = _run_loop(monkeypatch, game, [START, FIRE, {"quit": True}])
    assert calls == 3
    assert len(game.defense_missiles) == 1


def test_dead_base_cooldown_attribute_gone(start_screen_game):
    """Criterion 10: the unused ``MainGame.base_cooldown`` attribute is deleted."""
    game = start_screen_game()
    assert not hasattr(game, "base_cooldown")
    assert "base_cooldown" not in inspect.getsource(systems.game_loop)
