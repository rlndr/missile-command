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
COLOR_GROUND = (70, 90, 50)    # Dark olive ground strip

# Ground
GROUND_HEIGHT = 20                       # Height of the ground strip along the bottom
GROUND_Y = SCREEN_HEIGHT - GROUND_HEIGHT  # Top of the ground; buildings and the tower stand here

# Game timing constants
DT_DEFAULT = 1.0 / 60  # Delta time for 60 FPS

# Difficulty settings
BASE_SPAWN_INTERVAL = 3.5  # Seconds between incoming missile spawns
DIFFICULTY_RAMP_RATE = 0.05  # How much spawn rate decreases per second
MIN_SPAWN_INTERVAL = 2.0   # Fastest we'll ever spawn enemies
RAPID_FIRE_SPAWN_RATE_MULTIPLIER = 2  # Enemy spawn rate multiplier while rapid fire is on

# Missile speeds (pixels per second)
INCOMING_MISSILE_SPEED = 200
DEFENSE_MISSILE_SPEED = 380

# Enemy missile exhaust trail
ENEMY_TRAIL_SPACING = 6                    # Minimum px between trail samples
ENEMY_TRAIL_MAX_POINTS = 12                # Samples kept per missile (about 80 px of trail)
ENEMY_TRAIL_WIDTH = 2                      # Trail line width in px
ENEMY_TRAIL_HEAD_COLOR = COLOR_ORANGE      # Hot exhaust next to the missile
ENEMY_TRAIL_TAIL_COLOR = COLOR_GRAY        # Cooled smoke at the far end

# Defensive base settings
BASE_COOLDOWN_TIME = 1.5  # Seconds between missile launches from launcher
COOLDOWN_BAR_HEIGHT = 4  # Reload bar height in px
COOLDOWN_BAR_GAP = 4     # Px between the launcher's bottom edge and the reload bar
COOLDOWN_BAR_TRACK_COLOR = COLOR_DARK_BLUE  # Empty part of the reload bar
COOLDOWN_BAR_FILL_COLOR = COLOR_ORANGE      # Filled part while reloading
COOLDOWN_BAR_READY_COLOR = COLOR_YELLOW     # Full bar when the launcher can fire

# Rapid-fire window: repeats every minute of play, starting after the first minute
RAPID_FIRE_START_TIME = 60.0            # Seconds of play before the window opens
RAPID_FIRE_DURATION = 10.0              # Window length in seconds
RAPID_FIRE_INTERVAL = 60.0              # Seconds from one window opening to the next
RAPID_FIRE_COOLDOWN_TIME = 0.1          # Seconds between launches during the window
LAUNCHER_RAPID_FIRE_COLOR = COLOR_RED   # Tower body and barrel during the window

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

# City layout: two mirrored groups of buildings either side of the launcher
CITY_EDGE_MARGIN = 30   # Gap in px between the outer buildings and the screen edges
BUILDING_SPACING = 80   # Px from one building's left edge to the next in a group

# Explosion settings
EXPLOSION_MAX_RADIUS = 80
EXPLOSION_EXPANSION_TIME = 0.5
EXPLOSION_SHRINK_TIME = 0.3
BUILDING_EXPLOSION_MAX_RADIUS = 110
BUILDING_EXPLOSION_EXPANSION_TIME = 0.4
BUILDING_EXPLOSION_SHRINK_TIME = 0.5
BUILDING_EXPLOSION_LAYERS = ((1.0, COLOR_RED), (0.7, COLOR_ORANGE), (0.4, COLOR_YELLOW))
BUILDING_EXPLOSION_FLICKER_SPEED = 40.0
BUILDING_EXPLOSION_FLICKER_AMOUNT = 0.12

# Launcher tower, standing on the ground at the bottom centre
LAUNCHER_WIDTH = 60          # Tower body width
LAUNCHER_HEIGHT = 50         # Tower body height
LAUNCHER_BARREL_WIDTH = 8    # Barrel on top of the body
LAUNCHER_BARREL_HEIGHT = 16
LAUNCHER_X = SCREEN_WIDTH // 2                                    # Muzzle x (top centre of the barrel)
LAUNCHER_Y = GROUND_Y - LAUNCHER_HEIGHT - LAUNCHER_BARREL_HEIGHT  # Muzzle y; defense missiles start here

# Game states
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"

# Pause overlay
PAUSE_OVERLAY_COLOR = COLOR_BLACK  # Colour of the layer that dims the frozen battlefield
PAUSE_OVERLAY_ALPHA = 160          # Overlay opacity, 0-255 (scene ends up at about 37 % brightness)

# Scoring
MISSILE_INTERCEPT_POINTS = 10    # Points per enemy missile destroyed by a player explosion
SURVIVAL_POINTS_PER_SECOND = 1   # Points per whole second survived in play
HUD_MARGIN = 10                  # Gap in px between the HUD score and the top/right screen edges
WAVE_DURATION = 30.0             # Seconds of play per wave
HUD_WAVE_COLOR = COLOR_WHITE     # HUD wave text colour, distinct from the yellow score
HUD_WAVE_GAP = 24                # Gap in px between the HUD wave text and the score text

# High score
HIGH_SCORE_MAX = 999_999_999  # Largest stored high score that is believed

# Sound
SOUND_SAMPLE_RATE = 22050        # Samples per second requested from the mixer
SOUND_BUFFER_SIZE = 512          # Mixer buffer size in samples (low latency)
SOUND_VOLUME = 0.25              # Peak amplitude as a fraction of full scale
SOUND_FADE_TIME = 0.01           # Seconds of fade-out at the end of each square sweep
SOUND_NOISE_SEED = 0x2B5D        # Non-zero 15-bit LFSR seed for noise bursts
SOUND_LAUNCH_SWEEP = (330, 990, 0.15)       # Start Hz, end Hz, seconds
SOUND_INTERCEPT_SWEEP = (1200, 2400, 0.08)  # Start Hz, end Hz, seconds
SOUND_GAME_OVER_SWEEP = (440, 55, 1.0)      # Start Hz, end Hz, seconds
SOUND_EXPLOSION_NOISE = (4000, 0.5)         # Noise step Hz, seconds
SOUND_IMPACT_NOISE = (1200, 0.35)           # Noise step Hz, seconds
SOUND_LASER_SWEEP = (1800, 300, 0.08)       # Start Hz, end Hz, seconds (rapid-fire shot)
SOUND_TICK_TOCK = (880, 660, 0.06, 0.04, 0.08)  # Tick Hz, tock Hz, tick s, gap s, tock s (wave change)
SOUND_NAMES = ("launch", "explosion", "intercept", "impact", "game_over", "laser", "tick_tock")
