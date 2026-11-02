"""Tests for job 005-harden-load-score.

``ScoreSystem.load_high_score()`` never raises: a missing, unreadable or
malformed ``config.json`` (or an out-of-range value) loads as a high score of
0, good files still load, and loading never writes the file.
"""

import gc
import json
import os

import pygame
import pytest

import systems.score
from game.constants import COLOR_YELLOW, HIGH_SCORE_MAX, STATE_START
from systems.game_loop import MainGame
from systems.score import ScoreSystem
from tests.test_buildings_game_over import REAL_CONFIG_KEYS

FEATURE_CASES = [
    '{"high_score": "abc"}',
    "[]",
    "1e999",
    '{"high_score": ' + "1" * 4301 + "}",
]
FEATURE_IDS = ["str-abc", "empty-list", "top-level-1e999", "4301-digits"]


@pytest.fixture
def config_path(monkeypatch, tmp_path):
    """Point ``systems.score.CONFIG_PATH`` at a (not yet written) tmp file and return it."""
    path = tmp_path / "config.json"
    monkeypatch.setattr(systems.score, "CONFIG_PATH", str(path))
    return path


def _write(path, contents):
    """Write ``contents`` (``str`` or ``bytes``) to ``path``; return the bytes written."""
    data = contents if isinstance(contents, bytes) else contents.encode("utf-8")
    path.write_bytes(data)
    return data


def _assert_loads_as(path, contents, expected):
    """Write ``contents``, build a ScoreSystem, and check it loads ``expected`` read-only."""
    before = _write(path, contents)
    score_system = ScoreSystem()
    assert score_system.high_score == expected
    assert type(score_system.high_score) is int
    assert path.read_bytes() == before
    return score_system


# --- Criteria 1-6: file contents ----------------------------------------------

@pytest.mark.parametrize("contents", FEATURE_CASES, ids=FEATURE_IDS)
def test_feature_cases_load_as_zero(config_path, contents):
    """Criterion 1: the four crashing files from the feature load as 0."""
    _assert_loads_as(config_path, contents, 0)


@pytest.mark.parametrize("contents", [
    '{"high_score": 1e999}',
    '{"high_score": Infinity}',
    '{"high_score": -Infinity}',
    '{"high_score": NaN}',
    '{"high_score": null}',
    '{"high_score": [1]}',
    '{"high_score": {}}',
])
def test_other_non_numbers_load_as_zero(config_path, contents):
    """Criterion 2: non-numeric ``high_score`` values load as 0."""
    _assert_loads_as(config_path, contents, 0)


@pytest.mark.parametrize("contents", ['"abc"', "42", "null", "[1, 2]"])
def test_other_non_objects_load_as_zero(config_path, contents):
    """Criterion 3: a top-level value that isn't a JSON object loads as 0."""
    _assert_loads_as(config_path, contents, 0)


@pytest.mark.parametrize("contents", [
    "{not json",
    "",
    "[" * 200_000,
    b"\xff\xfe\x00{",
], ids=["not-json", "empty", "deep-nesting", "not-utf8"])
def test_unparseable_files_load_as_zero(config_path, contents):
    """Criterion 4: files that can't be decoded or parsed load as 0."""
    _assert_loads_as(config_path, contents, 0)


@pytest.mark.parametrize("contents", [
    '{"high_score": -5}',
    json.dumps({"high_score": HIGH_SCORE_MAX + 1}),
    json.dumps({"high_score": 10**4000}),
    json.dumps({"high_score": "1" * 4000}),
], ids=["negative", "max-plus-one", "4001-digit-int", "4000-digit-str"])
def test_out_of_range_values_load_as_zero(config_path, contents):
    """Criterion 5: values below 0 or above ``HIGH_SCORE_MAX`` load as 0."""
    _assert_loads_as(config_path, contents, 0)


@pytest.mark.parametrize("contents, expected", [
    ('{"high_score": 250}', 250),
    ('{"high_score": 0}', 0),
    (json.dumps({"high_score": HIGH_SCORE_MAX}), HIGH_SCORE_MAX),
    ('{"high_score": "120"}', 120),
    ("{}", 0),
    (json.dumps(REAL_CONFIG_KEYS), 50),
], ids=["250", "0", "max", "str-120", "no-key", "real-keys"])
def test_good_files_still_load(config_path, contents, expected):
    """Criterion 6: valid files load their high score."""
    _assert_loads_as(config_path, contents, expected)


# --- Criteria 7-8: missing and unreadable paths -------------------------------

def test_missing_file_loads_zero_and_is_not_created(config_path):
    """Criterion 7: no file loads as 0 and loading doesn't create one."""
    score_system = ScoreSystem()
    assert score_system.high_score == 0
    assert type(score_system.high_score) is int
    assert not config_path.exists()


def test_directory_path_loads_zero(config_path):
    """Criterion 8: ``CONFIG_PATH`` being a directory loads as 0."""
    config_path.mkdir()
    score_system = ScoreSystem()
    assert score_system.high_score == 0
    assert config_path.is_dir()


# --- Criteria 9-10: the game launches -----------------------------------------

@pytest.fixture
def bad_game(config_path):
    """Return a factory: write ``contents`` and build ``MainGame()``; cleaned up after."""
    gc.collect()

    def make(contents):
        _write(config_path, contents)
        return MainGame()

    yield make
    gc.collect()
    pygame.quit()


@pytest.mark.parametrize("contents", FEATURE_CASES, ids=FEATURE_IDS)
def test_game_launches_with_bad_file(bad_game, contents):
    """Criterion 9: a bad file still opens the start screen with "High Score: 0"."""
    game = bad_game(contents)
    assert game.state == STATE_START
    assert game.score_system.high_score == 0
    assert any(text == "High Score: 0" and color == COLOR_YELLOW
               for text, _size, color, _y in game.menu_lines())
    game.draw_start_screen()


def test_real_loop_runs_with_bad_file(bad_game, monkeypatch):
    """Criterion 10: the real loop starts and quits with a ``[]`` config."""
    game = bad_game("[]")
    monkeypatch.setattr(game, "handle_events", lambda: {"quit": True})
    game.start_game_loop()
    assert game.state == STATE_START


# --- Criteria 11-12: no writes ------------------------------------------------

@pytest.mark.parametrize("contents", [
    '{"high_score": "abc", "sound_enabled": false}',
    "[]",
], ids=["str-abc-with-keys", "empty-list"])
def test_bad_file_not_overwritten_after_fallback(config_path, contents):
    """Criterion 11: saving after a 0 fallback leaves the bad file alone."""
    score_system = _assert_loads_as(config_path, contents, 0)
    before = config_path.read_bytes()
    score_system.score = 120
    score_system.save_high_score()
    assert config_path.read_bytes() == before
    assert score_system.high_score == 120


@pytest.mark.parametrize("contents, expected", [
    ('{"high_score": 250}', 250),
    ("[]", 0),
], ids=["good-250", "bad-empty-list"])
def test_loading_is_read_only(config_path, contents, expected):
    """Criterion 12: repeated loads return the same value and never touch the file."""
    score_system = _assert_loads_as(config_path, contents, expected)
    before = config_path.read_bytes()
    mtime = os.path.getmtime(config_path)
    for _ in range(3):
        assert score_system.load_high_score() == expected
    assert config_path.read_bytes() == before
    assert os.path.getmtime(config_path) == mtime
