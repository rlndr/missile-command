#!/usr/bin/env bash
# The repo's checks. Exit 0 only when the branch is fit to review.
#
# The gate runs this script from the main checkout with the job's worktree as
# the working directory. Keep it fast, deterministic and non-interactive: no
# watch modes, no prompts, nothing that rewrites files.
#
# Python + Pygame, no project file: uv supplies pygame and pytest in a throwaway
# environment, so a fresh worktree needs no install step.
set -euo pipefail

export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export PYTHONDONTWRITEBYTECODE=1

# Every module compiles (catches syntax errors in files no test imports).
uv run -q --no-project --python 3.13 python -c '
import sys, pathlib
bad = 0
for p in pathlib.Path(".").rglob("*.py"):
    if ".worktrees" in p.parts or "factory" in p.parts:
        continue
    try:
        compile(p.read_text(), str(p), "exec")
    except SyntaxError as e:
        print(f"{p}:{e.lineno}: {e.msg}", file=sys.stderr); bad += 1
sys.exit(1 if bad else 0)
'

# The test suite, headless. -p no:cacheprovider keeps .pytest_cache out of the tree.
uv run -q --no-project --python 3.13 --with pygame --with pytest \
  python -m pytest -q -p no:cacheprovider tests
