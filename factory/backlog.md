# Backlog

`/factory next` takes the first unchecked item. Add one feature per line.

## Proof of concept — a basic playable game

- [x] Fix the crash when an enemy missile hits a building (screen shake passes a float to random.randint in MainGame.draw), and add the pytest harness: tests/conftest.py with SDL dummy drivers, plus a regression test that runs update/check_collisions/draw through a building hit → 001-fix-shake-crash
- [x] Defense missiles fly in a straight line to the clicked point and explode there; the explosion destroys every enemy missile inside its radius. Replace DefenseMissile's lookahead steering (missiles currently fly off-screen and never detonate) and drive Explosion growth/shrink from dt instead of pygame.time.get_ticks → 002-missiles-explode
- [x] Buildings and game over: only enemy missile impacts damage buildings (player explosions must not wreck the city), destroyed buildings stop counting, the game switches to GAME_OVER when no buildings are left (today destroyed buildings stay in the list, so it never ends), and the high score is saved once at game over → 003-buildings-game-over
- [x] Game states: open on the start screen and begin play on SPACE, ESC toggles pause/resume (no input emits "resume" today), SPACE restarts from GAME_OVER, and remove the SPACE-during-play branch that deletes standing buildings. Enemy spawn timing uses game time so pausing doesn't cause a burst of spawns → 004-game-states
- [x] Harden load_high_score() in systems/score.py: a malformed config.json ({"high_score": "abc"}, a top-level [], 1e999, an integer over 4300 digits) currently crashes the game at launch; fall back to a high score of 0 instead, matching how save_high_score() already handles bad files → 005-harden-load-score
- [x] Scoring: award points for each enemy missile destroyed by an explosion, and accumulate survival time correctly (add_survival_time truncates int(dt) to 0 every frame); the HUD score updates live during play → 006-scoring
- [x] Reset the launcher cooldown when a game starts or restarts, so the first click of a new game always fires → 007-reset-cooldown

## Later

- [x] Launcher cooldown indicator: draw a small bar under the launcher that fills as BASE_COOLDOWN_TIME elapses, so the player can see when they can fire again → 008-cooldown-indicator
- [x] Unit tests for collision detection and score calculation, as listed in GAME_DESIGN.md §13 → 011-collision-score-tests
- [x] Wave counter: every 30 seconds of play the wave number goes up and is shown in the HUD next to the score → 014-wave-counter
- [x] Pause overlay: when paused, dim the screen and list the controls → 017-pause-overlay
- [x] Pause screen text: replace "SPACE: Start / Restart" (SPACE does nothing while paused) with the keys that work there, ESC to resume → 017-pause-overlay
- [x] Building explosions: fix CollisionSystem.building_in_explosion so it measures from the nearest point on the building (today it measures from the top-left corner and misses blasts centred inside a building, e.g. Building(100, 500) with a blast at (130, 520) r=30 returns False), and when an enemy missile destroys a building, play a big, fiery explosion over it — larger than a defense blast, with layered orange/yellow/red fire that flickers and fades → 018-building-explosions
