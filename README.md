# Missile Command Clone

A Python/Pygame recreation of the classic 1980 Atari arcade game. Defend your city from a relentless barrage of incoming missiles by launching counter-missiles from your base. Difficulty increases over time as missiles spawn faster — see how long you can hold out.

## Features

- Click anywhere on screen to fire a defensive missile toward that point
- Explosions chain-react and can intercept incoming missiles mid-flight
- Buildings are damaged only by enemy missile impacts (3 hits destroy one); your own explosions never harm the city
- Score tracks missile hits and survival time, with high score persistence
- A wave counter next to the score goes up by one every 30 seconds of play
- Difficulty ramps up continuously as the game progresses
- Enemy missiles leave a short exhaust trail that fades from orange to grey smoke

## Requirements

- Python 3.x
- Pygame 2.x

## Installation

1. Clone or download this repository:
   ```bash
   git clone <repo-url>
   cd missile-command
   ```

2. Install Pygame:
   ```bash
   pip install pygame
   ```

## Running the Game

From the project root directory:

```bash
python3 main.py
```

## Running tests

The test suite uses `pytest`, which is a dev-only dependency (the game itself only needs Pygame). Tests run headless; from the project root:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q
```

Or, with `pygame` and `pytest` installed in your environment, `python -m pytest -q` (`tests/conftest.py` sets the SDL dummy drivers itself). Tests never write the real `config.json`.

## Controls

| Input | Action |
|-------|--------|
| Left Click | Launch a defensive missile toward the cursor |
| SPACE (start screen) | Start |
| ESC | Pause / Resume |
| M | Mute / unmute sound effects |
| SPACE (Game Over screen) | Restart |

## Gameplay

Your launcher tower stands on the ground at the bottom centre of the screen, between the two halves of the city, and your missiles rise from its barrel. Enemy missiles fall from the top of the screen toward your buildings along the bottom. Click to fire a counter-missile — when it reaches the target point it explodes, destroying any incoming missiles caught in the blast radius. Each enemy missile destroyed by your explosion scores `MISSILE_INTERCEPT_POINTS` (10) points, and every full second survived scores 1. The bar under the launcher fills in orange while it reloads and turns yellow when it can fire again. The retro-style sound effects for launches, explosions, intercepts, city hits and game over are generated in code from square waves and noise, with no audio files.

The game ends when all buildings are destroyed. Your final score and high score are displayed on the game over screen. Press SPACE to restart.
