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

## Next — arcade feel, fixes & gameplay depth

- [ ] Chain-reaction explosions: when an active player explosion destroys an IncomingMissile in MainGame.check_collisions, spawn a new player-attributed Explosion at the destroyed missile's position so blasts chain-react across nearby incoming missiles as promised in README.md
- [ ] Target crosshair and defense missile trails: draw a small crosshair (X) at each active DefenseMissile's target point while it is in flight, and draw a fading white-to-blue contrail behind DefenseMissile matching the style of IncomingMissile trails
- [ ] Fix building health bar colour and add building types: fix Building.draw_building passing a bare int instead of an RGB tuple for the health bar fill, and add "industrial" and "military" entries to BUILDING_TYPES in game/constants.py with distinct sizes, colours, damage thresholds, and score values as described in GAME_DESIGN.md
- [ ] Enemy missile aiming and ground impacts: in MainGame.spawn_incoming_missile aim across the target building's width instead of always targeting its left edge, remove the +50 y-offset in IncomingMissile.__init__ that skews trajectories below the target, and detonate incoming missiles that reach GROUND_Y with a small ground impact explosion
- [ ] Wire MainGame.check_collisions to use CollisionSystem (missile_to_building_collision and missile_in_explosion) instead of duplicating collision math inline, and remove dead code (ScoreDisplay in systems/score.py and MainGame.spawn_new_building in systems/game_loop.py)
- [ ] MIRV splitter missiles starting in wave 3: give incoming missiles spawned from wave 3 onward a chance to split mid-sky into 2–3 child IncomingMissiles aimed at different standing buildings, with a distinct visual colour or trail
- [ ] Launcher stun on direct hit: when an IncomingMissile hits DefensiveBase (using CollisionSystem.missile_to_base_collision), destroy the missile with an explosion and knock the launcher offline (is_active = False) for a short stun duration before it comes back online
