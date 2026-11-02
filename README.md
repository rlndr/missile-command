# Missile Command Clone

A Python/Pygame recreation of the classic 1980 Atari arcade game. Defend your city from a relentless barrage of incoming missiles by launching counter-missiles from your base. Difficulty increases over time as missiles spawn faster — see how long you can hold out.

## Features

- Click anywhere on screen to fire a defensive missile toward that point
- Explosions chain-react and can intercept incoming missiles mid-flight
- Buildings take damage and are destroyed by explosions
- Score tracks missile hits and survival time, with high score persistence
- Difficulty ramps up continuously as the game progresses

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

## Controls

| Input | Action |
|-------|--------|
| Left Click | Launch defensive missile toward cursor |
| SPACE | Pause / Resume |
| ESC | Pause |
| SPACE (on Game Over screen) | Restart |

## Gameplay

Your launcher sits in the top-left corner of the screen. Enemy missiles fall from the top of the screen toward your buildings along the bottom. Click to fire a counter-missile — when it reaches the target point it explodes, destroying any incoming missiles caught in the blast radius.

The game ends when all buildings are destroyed. Your final score and high score are displayed on the game over screen. Press SPACE to restart.
