"""Tests for doubled enemy spawns during the rapid-fire window (job 016).

While ``MainGame.rapid_fire_active()`` is true, ``current_spawn_interval()``
divides the floored spawn ramp by ``RAPID_FIRE_SPAWN_RATE_MULTIPLIER``, so the
window gets twice as many incoming missiles. Each spawn still makes one
missile and one ``update()`` still spawns at most one.
"""

import inspect
import os

import pytest

from game import constants
from game.constants import BASE_SPAWN_INTERVAL, MIN_SPAWN_INTERVAL
from systems.game_loop import MainGame

STEP = 0.25
REAL_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.json")


def recorder(monkeypatch, game):
    """Replace ``game.spawn_incoming_missile`` and return the list of spawn times."""
    times = []
    monkeypatch.setattr(game, "spawn_incoming_missile",
                        lambda: times.append(game.game_time))
    return times


def step_from(game, t0, steps):
    """Set ``game_time`` and ``last_spawn_time`` to ``t0``, then call ``update(STEP)`` ``steps`` times."""
    game.game_time = t0
    game.last_spawn_time = t0
    for _ in range(steps):
        game.update(STEP)


def interval_at(game, t):
    """Return ``current_spawn_interval()`` with ``game_time`` set to ``t``."""
    game.game_time = t
    return game.current_spawn_interval()


# 1. Constant

def test_spawn_rate_multiplier_constant():
    """The multiplier is 2 and the ramp constants are unchanged."""
    assert constants.RAPID_FIRE_SPAWN_RATE_MULTIPLIER == 2
    assert BASE_SPAWN_INTERVAL == 3.5
    assert MIN_SPAWN_INTERVAL == 2.0


# 2. Interval values

@pytest.mark.parametrize("t, expected", [
    (0.0, 3.5),
    (30.0, pytest.approx(3.5 / 1.5)),
    (45.0, 2.0),
    (59.99, 2.0),
    (70.0, 2.0),
    (100.0, 2.0),
])
def test_interval_outside_window_is_the_normal_ramp(main_game, t, expected):
    """Outside the window the interval is the ramped-and-floored value."""
    assert interval_at(main_game, t) == expected


@pytest.mark.parametrize("t", [60.0, 65.0, 69.99])
def test_interval_inside_window_is_halved_after_floor(main_game, t):
    """Inside the window the floored 2.0 s is halved to 1.0 s."""
    assert interval_at(main_game, t) == 1.0


# 3. Rapid fire read only through rapid_fire_active()

def test_interval_multiplier_applies_to_ramped_value(main_game, monkeypatch):
    """Forcing rapid fire on early halves the ramped interval, not the floor."""
    monkeypatch.setattr(main_game, "rapid_fire_active", lambda: True)
    assert interval_at(main_game, 0.0) == 1.75
    assert interval_at(main_game, 30.0) == pytest.approx(3.5 / 1.5 / 2)


def test_interval_ignores_game_time_when_rapid_fire_forced_off(main_game, monkeypatch):
    """Forcing rapid fire off inside the 013 window gives the normal 2.0 s."""
    monkeypatch.setattr(main_game, "rapid_fire_active", lambda: False)
    assert interval_at(main_game, 65.0) == 2.0


def test_interval_follows_repeating_window_rule(main_game, monkeypatch):
    """With 015's repeating rule patched in, the doubling follows every window."""
    game = main_game
    monkeypatch.setattr(
        game, "rapid_fire_active",
        lambda: game.game_time >= 60.0 and (game.game_time - 60.0) % 60.0 < 10.0)
    assert interval_at(game, 125.0) == 1.0
    assert interval_at(game, 185.0) == 1.0
    assert interval_at(game, 100.0) == 2.0
    assert interval_at(game, 130.0) == 2.0


def test_interval_code_has_no_window_time_logic():
    """``current_spawn_interval()`` doesn't read the window constants itself."""
    source = inspect.getsource(MainGame.current_spawn_interval)
    assert "rapid_fire_active()" in source
    assert "RAPID_FIRE_START_TIME" not in source
    assert "RAPID_FIRE_DURATION" not in source


# 4. Twice as many spawns across a window

def test_window_gets_twice_as_many_spawns(main_game, monkeypatch):
    """Ten seconds inside the window spawn 10 missiles; outside, 5."""
    game = main_game
    times = recorder(monkeypatch, game)
    step_from(game, 59.75, 40)
    assert times == [60.75 + i for i in range(10)]
    inside = len(times)

    times = recorder(monkeypatch, game)
    step_from(game, 89.75, 40)
    assert times == [91.75, 93.75, 95.75, 97.75, 99.75]
    outside = len(times)

    assert inside == constants.RAPID_FIRE_SPAWN_RATE_MULTIPLIER * outside


# 5. Entering the window

def test_first_window_frame_spawns_after_one_second(main_game, monkeypatch):
    """At 60.0 s, 1.0 s since the last spawn is already enough."""
    times = recorder(monkeypatch, main_game)
    step_from(main_game, 59.0, 12)
    assert times == [60.0, 61.0, 62.0]


# 6. Leaving the window

def test_leaving_window_returns_to_normal_interval(main_game, monkeypatch):
    """No spawn at 70.0 s; the next one is 2.0 s after the last."""
    times = recorder(monkeypatch, main_game)
    step_from(main_game, 69.0, 12)
    assert times == [71.0]


# 7. Still one missile per spawn and per frame

def test_real_spawns_make_one_missile_each(main_game):
    """Real spawns add one missile each: 2 in the window, 1 outside."""
    game = main_game
    step_from(game, 59.75, 8)
    assert len(game.incoming_missiles) == 2

    game.incoming_missiles = []
    step_from(game, 89.75, 8)
    assert len(game.incoming_missiles) == 1


def test_huge_dt_spawns_at_most_once(main_game, monkeypatch):
    """One long frame inside the window still spawns only once."""
    game = main_game
    times = recorder(monkeypatch, game)
    game.game_time = 60.0
    game.last_spawn_time = 0.0
    game.update(5.0)
    assert len(times) == 1


# 8. Pause freezes the doubled rate

def test_pause_freezes_doubled_rate(main_game, monkeypatch):
    """No spawns or time pass while paused; the doubled rate resumes after."""
    game = main_game
    times = recorder(monkeypatch, game)
    game.game_time = 65.0
    game.last_spawn_time = 65.0
    game.handle_actions({"toggle_pause": True})
    for _ in range(600):
        game.handle_actions({})
    game.handle_actions({"toggle_pause": True})
    assert times == []
    assert game.game_time == 65.0

    for _ in range(4):
        game.update(STEP)
    assert times == [66.0]


# 9. New game resets

def test_new_game_resets_spawn_interval(main_game):
    """``start_game()`` after a window goes back to the base interval."""
    game = main_game
    step_from(game, 59.75, 8)
    game.start_game()
    assert game.game_time == 0.0
    assert game.last_spawn_time == 0.0
    assert game.current_spawn_interval() == BASE_SPAWN_INTERVAL


# 10. Launcher behaviour unchanged

def test_launcher_rapid_fire_follows_window(main_game):
    """The launcher's rapid-fire flag still tracks ``rapid_fire_active()``."""
    game = main_game
    step_from(game, 59.75, 4)
    assert game.base.rapid_fire is True
    assert game.base.rapid_fire == game.rapid_fire_active()

    step_from(game, 89.75, 4)
    assert game.base.rapid_fire is False
    assert game.rapid_fire_active() is False


# 11. Real config.json untouched

def test_real_config_untouched(main_game):
    """Playing through a window doesn't change the real config.json."""
    before = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    game = main_game
    step_from(game, 59.75, 40)
    game.check_collisions()
    game.score_system.save_high_score()
    after = open(REAL_CONFIG, "rb").read() if os.path.exists(REAL_CONFIG) else None
    assert before == after
