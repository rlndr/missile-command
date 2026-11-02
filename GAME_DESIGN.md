# Missile Command - Game Design Document

## 1. Game Overview

### Core Concept
Real-time vertical defense game where players protect cities from incoming enemy missiles by launching defensive counter-attacks. Classic arcade-style gameplay with increasing difficulty.

### Target Audience
- Casual gamers (arcade-style action)
- Retro enthusiasts
- Python/Pygame learners
- Quick session play (30-60 minutes per run)

## 2. Technical Architecture

### Tech Stack
- **Language:** Python 3.x
- **Library:** Pygame
- **Architecture:** Object-Oriented + Game Loop pattern
- **Rendering:** 2D sprites with collision detection
- **Target Resolution:** 800x600 (scaled if needed)

### Project Structure
```
missile-command/
├── main.py                 # Entry point, game loop
├── game/
│   ├── __init__.py
│   ├── game.py            # MainGame class (game state manager)
│   └── constants.py       # Game constants & config
├── entities/
│   ├── __init__.py
│   ├── missile.py         # Base Missile class + subclasses
│   ├── base.py            # Defensive base launcher
│   ├── terrain.py         # Buildings, obstacles, destructible terrain
│   └── explosion.py       # Explosion effects with damage radius
├── systems/
│   ├── __init__.py
│   ├── input_system.py    # Player input handling (keyboard)
│   ├── physics.py         # Movement, collision detection
│   └── score.py           # Score tracking & display
├── utils/
│   ├── __init__.py
│   ├── vector_math.py     # Vector2 operations
│   └── timer.py           # Delta time & frame counter
├── assets/                 # Images, sounds (optional)
└── config.json             # Loadable settings
```

## 3. Core Game Loop

### Main Loop Structure
```python
while running:
    handle_events()     # Keyboard input
    update(dt)          # dt = delta time in seconds
    draw()              # Render everything
    check_conditions()  # Win/lose states
```

### Update Cycle (per frame)
1. Spawn incoming missiles (timer-based)
2. Update all entities (movement, collisions)
3. Handle explosions & damage
4. Score calculations
5. Difficulty ramp-up (increase spawn rate)
6. Check game-over conditions

## 4. Core Entities

### 4.1 Missile Classes

#### IncomingMissile (Enemy)
```
Properties:
  - position: Vector2 (x, y)
  - velocity: Vector2 (moves diagonally from top-right to city)
  - speed: 150-250 px/sec
  - target: Vector2 (city location or building)
  - is_destroyed: bool

Behavior:
  - Moves linearly toward target point
  - Leaves trail of particles on death
  - Triggers explosion on death OR impact
  - Has damage radius on destruction (can destroy defensive base if close)
```

#### DefenseMissile (Player)
```
Properties:
  - position: Vector2 (starts at top-left launcher)
  - velocity: Vector2 (moves diagonally from top-left to target)
  - speed: 300-400 px/sec (faster than enemy)
  - turn_rate: max turning radius for curve shots
  - is_destroyed: bool

Behavior:
  - Launched by player clicking/dragging on screen
  - Moves in curved trajectory toward target
  - Leaves trail of particles
  - Can be destroyed by incoming missile explosion (if close)
```

### 4.2 Defensive Base
```
Properties:
  - position: Vector2 (top-left corner of play area)
  - is_active: bool (can launch missiles)
  - health: int (can take damage, goes offline if destroyed)
  - cooldown: float (missile reload time between shots)

Behavior:
  - Stationary launcher at top-left
  - Cooldown timer after each missile launch
  - Visual indicator when on cooldown/offline
  - Can be knocked out by nearby explosions
```

### 4.3 Terrain/Buildings
```
Properties:
  - buildings: list of Building objects
  - terrain: list of Obstacle objects (optional destructible elements)

Building Types:
  - Residential: Low health, high priority score value
  - Industrial: Medium health/medium score
  - Military: High health, highest score value
  - Critical: Special buildings with unique properties

Each Building has:
  - position, size, health_max, health_current
  - damage_threshold: explosions needed to destroy
  - score_value: points when destroyed
  - render_type: visual appearance
```

### 4.4 Explosion
```
Properties:
  - position: Vector2 (center point)
  - radius: float (damage/blast radius)
  - max_radius: float (expands to full size over time)
  - expansion_speed: float
  - is_active: bool (shrinks and fades out)

Behavior:
  - Instant creation at target position with initial small radius
  - Expands over first ~0.5 seconds to max_radius
  - Shrinks back to nothing over next ~0.3 seconds
  - Deals damage to any entity within radius at appropriate phase
  - Leaves particle effects as it dissipates
```

## 5. Game States

### State Machine
```
START_SCREEN  -> PLAYING   (spacebar/click)
PLAYING        -> PAUSED    (ESC key)
PAUSED         -> RESUMING  (click "Resume")
RESUMING       -> PLAYING
PLAYING        -> GAME_OVER (all buildings destroyed or time limit)
```

### Start Screen
- Title display
- Instructions (WASD: none, Mouse: click to launch defense missile)
- Score reset option
- High score display (saved in config file)
- "Press SPACE" prompt

### Playing State
- Main gameplay loop
- Difficulty scales over time
- Spawn rate increases gradually
- Damage accumulates
- Score counter visible

### Game Over States
**Lose Conditions:**
- All buildings destroyed
- Time limit reached (optional)

**Win Condition:**
- No lose conditions met for extended period (or optional "survive X waves")

## 6. Input System

### Keyboard Controls
| Key | Action |
|-----|--------|
| Mouse Click/Right-Click | Launch defensive missile at location |
| SPACE | Start/Pause game toggle |
| ESC | Pause/Resume, Back to menu |

### Mouse Interaction
- Click anywhere on screen: launches defense missile toward that point
- Right-click (optional): alternate fire or different shot type
- No keyboard navigation (mouse-driven aiming)

## 7. Physics & Collision Detection

### Movement System
- **Linear missiles:** Direct path from A to B
- **Trajectory missiles:** Follow curved vector math for realistic arcs
- All use Vector2 positions with speed * delta_time

### Collision Types
1. **AABB Collision (Rectangles):** Buildings vs other rect objects
2. **Circle Collision:** Missiles, explosions, projectiles
   - Distance between centers < sum of radii
3. **Point-in-Region:** Explosion damage area check

### Collision Response
```python
def check_collision(obj1, obj2):
    if isinstance(obj, IncomingMissile) and isinstance(other, DefenseMissile):
        destroy_both(obj, other)
    elif isinstance(obj, Building) and obj in explosion.damage_list:
        deal_explosion_damage(building, explosion)
    elif obj in building.collision_objects:
        handle_building_collision(obj, building)
```

## 8. Score System

### Scoring Rules
- **Defense Missile Hit Enemy:** +10 points (instant destroy)
- **Enemy Explosion on Building:** Building health damage
- **Building Destroyed:** +50 points (Residential), +75 (Industrial), +100 (Military/Critical)
- **Survival Bonus:** +1 point per second survived

### Score Display
- Top-right corner: current score
- High score in title bar/menu
- Optional: kill feed showing recent destructions

## 9. Difficulty Progression

### Wave System (optional enhancement)
```
Wave 1: 1 incoming missile every 3 seconds
Wave 2+: spawn rate increases by ~10% per wave
Each wave adds new buildings or terrain features
```

### Continuous Ramp-up (primary system)
```
Spawn rate starts at base_interval
Increases over time: current_interval = base * (time/60 + 1)
Every 30 seconds spawn rate decreases further
At least one incoming missile appears every 5-7 seconds minimum
```

## 10. Visual Design Elements

### Required Sprites
1. **Top launcher** (base icon)
2. **Incoming missile** (red or enemy color)
3. **Defense missile** (white/yellow trajectory)
4. **Building sprites** (3-4 types, front/back for Z-sorting)
5. **Explosion frames** (4 stages of expansion/decay)

### Visual Effects
- Particle trails on missiles
- Shockwave rings on explosions
- Smoke effects from destroyed buildings
- Flash effects on building destruction
- Screen shake on large explosions (optional)

### Color Palette (suggestions)
- Background: Dark blue/black city night
- Incoming missiles: Red/orange
- Defense missiles: White/yellow
- Buildings: Various colors by type
- UI elements: Yellow/white text

## 11. Data Structures

### GameState Class
```python
class GameState:
    buildings = []         # List of Building objects
    incoming_missiles = [] # List of IncomingMissile
    defense_missiles = []  # List of DefenseMissile
    explosions = []        # List of Explosion
    score = 0              # Current score
    difficulty = 1.0       # Multiplier for spawn rates
    game_time = 0          # Seconds elapsed
    buildings_left = count()  # How many intact
    
    # Launchers
    base = DefensiveBase()
    base_cooldown = 0.0
```

### Entity Base Class
```python
class GameEntity:
    def __init__(self, x, y):
        self.position = Vector2(x, y)
        self.velocity = Vector2(0, 0)
        self.is_destroyed = False
    
    def apply_velocity(self, dt):
        self.position += self.velocity * dt
    
    def handle_collision(self, other_entity):
        # Collision logic for subclasses
        pass
    
    def is_active(self):
        return not self.is_destroyed
```

## 12. Implementation Phases

### Phase 1: Setup (Week 1)
- [ ] Initialize Pygame and create project structure
- [ ] Implement game loop and delta time handling
- [ ] Create basic input system
- [ ] Render static background/cityscape

### Phase 2: Core Mechanics (Week 1-2)
- [ ] Implement DefensiveBase launcher
- [ ] Create IncomingMissile with movement
- [ ] Create DefenseMissile with click-based launch
- [ ] Implement collision detection (circle-circle, rect-collision)
- [ ] Basic explosion system

### Phase 3: Buildings & Terrain (Week 2-3)
- [ ] Add building spawning system
- [ ] Building health and destruction logic
- [ ] Visual representation of buildings
- [ ] Score tracking per building type

### Phase 4: Game State Management (Week 3)
- [ ] Start screen with instructions
- [ ] Playing state with game loop integration
- [ ] Game over detection and display
- [ ] High score persistence

### Phase 5: Polish & Features (Week 4+)
- [ ] Particle effects and visual feedback
- [ ] Difficulty ramp-up system
- [ ] Sound effects (optional)
- [ ] UI improvements
- [ ] Bug fixes and optimization

## 13. Testing Strategy

### Unit Tests (pytest)
- Collision detection accuracy
- Movement speed consistency
- Score calculation correctness
- Explosion damage radius testing

### Playtest Checklist
- [ ] Can launch defense missiles from top-left launcher
- [ ] Incoming missiles spawn at random positions and move downward-left
- [ ] Clicking screen launches missile to target point
- [ ] Buildings take explosion damage correctly
- [ ] Score updates on hits/destruction
- [ ] Game ends when appropriate
- [ ] Performance remains smooth (60 FPS)

## 14. Potential Enhancements (Future)

- Sound effects and background music
- Particle system enhancements
- Achievement/unlockable skins
- Multiplayer (hot-seat or online)
- Campaign/story mode with increasing difficulty
- Power-ups (double shots, slower enemy missiles)
- Save/load game progress
- Level editor for custom maps

## 15. Development Notes & Pitfalls

### Common Issues to Avoid
1. **Delta time inconsistencies:** Always use dt in update methods
2. **Memory leaks:** Clear destroyed objects from lists each frame
3. **Performance:** Limit entity counts (max ~100-150 active missiles)
4. **Z-ordering:** Render explosions last so they appear "in front"
5. **Frame rate sensitivity:** Use delta time for all movement calculations

### Optimization Tips
- Use sprite groups and pygame.sprite.Group for efficient collision queries
- Pool objects instead of creating/destroying frequently (explosions, missiles)
- Limit building spawn rate based on available screen space
- Cull off-screen particles after they expire

---

**Next Steps:**
1. Review this plan and let me know if adjustments needed
2. I'll create the first Python files with basic structure
3. Start with main.py and simple game loop
4. Build out each module incrementally

Would you like me to start implementing, or would you like to adjust any aspects of this design?