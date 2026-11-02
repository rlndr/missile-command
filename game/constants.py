"""Game constants and configuration settings."""

# Screen resolution
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32  # Pixel size for grid-based elements if needed

# Color definitions (RGB tuples)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (200, 50, 50)      # Enemy missiles
COLOR_ORANGE = (255, 140, 50)  # Explosions
COLOR_YELLOW = (255, 255, 50)  # Defense missiles
COLOR_GRAY = (80, 80, 80)      # Buildings
COLOR_BLUE = (50, 100, 200)    # Background night sky gradient
COLOR_DARK_BLUE = (30, 40, 60) # Darker night background

# Game timing constants
DT_DEFAULT = 1.0 / 60  # Delta time for 60 FPS

# Difficulty settings
BASE_SPAWN_INTERVAL = 3.5  # Seconds between incoming missile spawns
DIFFICULTY_RAMP_RATE = 0.05  # How much spawn rate decreases per second
MIN_SPAWN_INTERVAL = 2.0   # Fastest we'll ever spawn enemies

# Missile speeds (pixels per second)
INCOMING_MISSILE_SPEED = 200
DEFENSE_MISSILE_SPEED = 380

# Defensive base settings
BASE_COOLDOWN_TIME = 1.5  # Seconds between missile launches from launcher

# Building settings
BUILDING_TYPES = {
    "residential": {
        "color": COLOR_GRAY,
        "health_max": 100,
        "score_value": 50,
        "damage_threshold": 3,  # Number of explosions to destroy
        "width": 60,
        "height": 40
    }
}

# Explosion settings
EXPLOSION_MAX_RADIUS = 80
EXPLOSION_EXPANSION_TIME = 0.5
EXPLOSION_SHRINK_TIME = 0.3

# Launcher position (top-left corner)
LAUNCHER_X_OFFSET = 20
LAUNCHER_Y_OFFSET = 20

# Game states
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
