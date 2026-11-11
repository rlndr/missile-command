"""Tests for the per-minute enemy spawn rate step (issue #1).

After every completed ``SPAWN_STEP_DURATION`` of play, ``current_spawn_interval()``
divides the ramped-and-floored interval by a further ``SPAWN_STEP_MULTIPLIER``
(compounding), never going below ``HARD_MIN_SPAWN_INTERVAL``. Rapid fire still
halves the result last. Rapid fire is forced on or off here to isolate the step
from the rapid-fire window.
"""

import pytest

from game import constants
from game.constants import BASE_SPAWN_INTERVAL

STEP = 0.25


def interval_at(game, t):
    """Return ``current_spawn_interval()`` with ``game_time`` set to ``t``."""
    game.game_time = t
    return game.current_spawn_interval()


def force_rapid_fire(monkeypatch, game, on):
    """Make ``game.rapid_fire_active()`` always return ``on``."""
    monkeypatch.setattr(game, "rapid_fire_active", lambda: on)


# 1. Constants

def test_step_constants():
    """The step, multiplier and hard minimum are defined; the ramp floor is unchanged."""
    assert constants.SPAWN_STEP_DURATION == 60.0
    assert constants.SPAWN_STEP_MULTIPLIER == 1.1
    assert constants.HARD_MIN_SPAWN_INTERVAL == 0.5
    assert constants.MIN_SPAWN_INTERVAL == 2.0


# 2. First minute unchanged

@pytest.mark.parametrize("t, expected", [
    (0.0, 3.5),
    (30.0, pytest.approx(3.5 / 1.5)),
    (45.0, 2.0),
    (59.99, 2.0),
])
def test_first_minute_unchanged(main_game, monkeypatch, t, expected):
    """Before 60 s the interval is the existing ramp floored at 2.0 s."""
    force_rapid_fire(monkeypatch, main_game, False)
    assert interval_at(main_game, t) == expected


# 3. Step boundaries

def test_first_step_lands_at_60_seconds(main_game, monkeypatch):
    """The interval drops from 2.0 s to 2.0 / 1.1 exactly at 60 s."""
    force_rapid_fire(monkeypatch, main_game, False)
    assert interval_at(main_game, 59.99) == 2.0
    assert interval_at(main_game, 60.0) == pytest.approx(2.0 / 1.1)


def test_second_step_lands_at_120_seconds(main_game, monkeypatch):
    """The interval drops from 2.0 / 1.1 to 2.0 / 1.1**2 exactly at 120 s."""
    force_rapid_fire(monkeypatch, main_game, False)
    assert interval_at(main_game, 119.99) == pytest.approx(2.0 / 1.1)
    assert interval_at(main_game, 120.0) == pytest.approx(2.0 / 1.1**2)


# 4. Compounding

@pytest.mark.parametrize("n", range(1, 7))
def test_steps_compound(main_game, monkeypatch, n):
    """Mid-way through minute ``n`` the interval is 2.0 / 1.1**n."""
    force_rapid_fire(monkeypatch, main_game, False)
    assert interval_at(main_game, 60.0 * n + 30.0) == pytest.approx(2.0 / 1.1**n)


# 5. Hard minimum

def test_hard_minimum_holds(main_game, monkeypatch):
    """The interval keeps stepping until it reaches 0.5 s, then stays there."""
    force_rapid_fire(monkeypatch, main_game, False)
    assert interval_at(main_game, 840.0) == pytest.approx(2.0 / 1.1**14)
    assert interval_at(main_game, 900.0) == 0.5
    assert interval_at(main_game, 1800.0) == 0.5
    assert interval_at(main_game, 3600.0) == 0.5


# 6. Rapid fire applied last

def test_rapid_fire_halves_stepped_interval(main_game, monkeypatch):
    """Rapid fire halves the stepped interval, including below the hard minimum."""
    force_rapid_fire(monkeypatch, main_game, True)
    assert interval_at(main_game, 90.0) == pytest.approx(2.0 / 1.1 / 2)
    assert interval_at(main_game, 3600.0) == 0.25


# 7. New game resets

def test_new_game_resets_step(main_game):
    """``start_game()`` after ten minutes goes back to the base interval."""
    game = main_game
    game.game_time = 600.0
    game.start_game()
    assert game.current_spawn_interval() == BASE_SPAWN_INTERVAL


# 8. Real spawns follow the stepped rate

def test_spawns_follow_stepped_rate(main_game, monkeypatch):
    """At step 2 (about 1.653 s) the first spawn lands on the 151.75 s frame."""
    game = main_game
    force_rapid_fire(monkeypatch, game, False)
    times = []
    monkeypatch.setattr(game, "spawn_incoming_missile",
                        lambda: times.append(game.game_time))
    game.game_time = 150.0
    game.last_spawn_time = 150.0
    for _ in range(8):
        game.update(STEP)
    assert times == [151.75]
