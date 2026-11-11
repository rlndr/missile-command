"""Shared pytest configuration and fixtures for headless game tests.

The SDL environment variables are set at module import time, before any
module (directly or transitively) imports ``pygame``, so the suite runs
without a display or audio device.
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT in sys.path:
    sys.path.remove(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

import gc  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import systems.game_loop  # noqa: E402
import systems.score  # noqa: E402
from game.constants import BUILDING_TYPES, STATE_PLAYING  # noqa: E402
from systems.game_loop import MainGame  # noqa: E402


@pytest.fixture
def main_game(monkeypatch, tmp_path):
    """Yield a started, playing ``MainGame`` isolated from the real config.json.

    ``systems.score.CONFIG_PATH`` is redirected to a file under ``tmp_path``
    before ``MainGame()`` is built, because ``ScoreSystem.__init__`` reads it.
    ``last_spawn_time`` is pushed to infinity so ``update()`` never spawns a
    random incoming missile during a test.

    The starting city is pinned to residential buildings: the fixture
    monkeypatches ``systems.game_loop.BUILDING_TYPES`` to a dict holding only
    "residential" before ``start_game()``, for the whole test, so later
    ``start_game()`` calls are residential too. To get the full set back,
    monkeypatch the name back to ``game.constants.BUILDING_TYPES`` and call
    ``start_game()`` again.
    """
    # Collect any stale game from an earlier test now, so its __del__
    # (which calls pygame.quit()) can't fire in the middle of this test.
    gc.collect()

    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(systems.game_loop, "BUILDING_TYPES",
                        {"residential": BUILDING_TYPES["residential"]})

    game = MainGame()
    game.start_game()
    game.state = STATE_PLAYING
    game.last_spawn_time = float("inf")

    yield game

    del game
    gc.collect()
    pygame.quit()
