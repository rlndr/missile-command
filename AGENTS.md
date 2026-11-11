# AGENTS.md

A Python 3 + Pygame arcade game in the missile defence genre. `README.md`
covers features and controls; `GAME_DESIGN.md` describes the design and where
it's headed. Read the parts that touch the area you change.

## Layout

- `main.py`: entry point.
- `systems/game_loop.py`: `MainGame`, the loop, states, collisions and drawing.
- `entities/`: missiles, explosions, buildings, the launcher.
- `systems/`: score and high score (`systems/score.py`), sound, collisions.
- `game/constants.py`: every tunable (sizes, colours, timings, states).
- `utils/`: helpers.
- `tests/`: pytest; `tests/conftest.py` sets the SDL dummy drivers.
- `config.json`: the player's saved high score and settings. Tracked, but tests
  must never write it.

## Setup

No install step. The game needs only Pygame; `uv` supplies Pygame and pytest
in a throwaway environment, so a fresh checkout or worktree is ready as is.
There are no env files.

## Run

```bash
uv run --no-project --python 3.13 --with pygame python main.py
```

It opens a window, so agents don't run it; render frames headless instead
(below). There is no dev server.

## Validate

`factory/checks.sh` is the source of truth. It checks every module compiles,
then runs the tests headless:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q tests
```

`pytest.ini` limits collection to `tests/`, so the copies in `.worktrees/`
are never collected from the repo root.

## Conventions

- Every tunable (sizes, colours, timings) is a constant in `game/constants.py`,
  imported with `from game.constants import *`. No literal RGB tuples elsewhere.
- Module, class and method docstrings; 4-space indent; snake_case.
- Movement and timers use `dt`, never wall-clock ticks. Destroyed entities are
  filtered out of their lists each frame.
- No new dependencies beyond Pygame unless the spec says so. Sounds are
  synthesised in code; there are no asset files.
- Tests never write the real `config.json`: monkeypatch
  `systems.score.CONFIG_PATH` to a `tmp_path` file.
- New behaviour gets a test in `tests/test_<feature>.py`.
- When features or controls change, update the README's Features, Controls or
  Gameplay sections.

## Headless frames

To see the game, or drive it from a script, run this in the checkout with
`<dir>` from `mktemp -d`, then Read the PNG:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame python -c "
import pygame, sys
from systems.game_loop import MainGame
from game.constants import STATE_PLAYING
g = MainGame(); g.start_game(); g.state = STATE_PLAYING
for _ in range(120): g.update(1/60)
g.draw(); pygame.image.save(g.screen, sys.argv[1] + '/frame.png')" <dir>
```

Other states: `STATE_START` (or `g.draw_start_screen()`), `STATE_PAUSED` and
`STATE_GAME_OVER` from `game.constants`. Post input with
`pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)))`
before `g.update(...)`.

## Software factory

`/factory run` builds every open GitHub issue labeled `factory` through
intake → spec → build → gate → review → approve, one PR per issue. State is in
`factory/jobs/` (gitignored); `factory/bin/job` is its only writer. Checks:
`factory/checks.sh`. Dashboard: `cd factory && python3 -m http.server`, then
open http://localhost:8000/dashboard.html.

Each job works in its own git worktree, a full checkout of the repo at
`.worktrees/<job-id>` (gitignored). A tool run from the repo root that doesn't
read `.gitignore` sees those copies too; exclude `.worktrees/` in its config.

`factory/v1-archive/` holds the jobs, board and backlog from the earlier
version of the factory, for reference only.
