"""Defensive base launcher."""

import pygame
from game.constants import *
from entities import GameEntity


class DefensiveBase(GameEntity):
    """Player's defensive missile launcher at top-left corner."""
    
    def __init__(self):
        # Position is fixed at top-left
        super().__init__(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)
        
        self.cooldown_time = BASE_COOLDOWN_TIME
        self.is_active = True
        self.width = 60
        self.height = 30
        
        # Visual offset for rendering
        self.render_offset_x = -15
        self.render_offset_y = -20
    
    def can_fire(self):
        """Check if base can fire another missile."""
        return self.is_active and self.cooldown_time <= 0
    
    def start_cooldown(self):
        """Start cooldown after firing a missile."""
        if self.is_active:
            self.cooldown_time = BASE_COOLDOWN_TIME
    
    def update(self, dt):
        """Update cooldown timer."""
        if not self.is_active:
            return
        
        self.cooldown_time = max(0, self.cooldown_time - dt)
        
        # Visual indicator for cooldown
        self.cooldown_ratio = min(1.0, self.cooldown_time / BASE_COOLDOWN_TIME)
    
    def get_bounds(self):
        """Get rectangular bounds for collision detection."""
        return pygame.Rect(
            self.position.x + self.render_offset_x,
            self.position.y + self.render_offset_y,
            self.width,
            self.height
        )
    
    def draw_base(self, screen, active_color=COLOR_WHITE, inactive_color=COLOR_GRAY):
        """Draw the base launcher."""
        
        if not self.is_active:
            color = inactive_color
            # Add visual indicator that base is offline
            pygame.draw.rect(screen, COLOR_RED, self.get_bounds(), 3)
        else:
            color = active_color
        
        # Draw main launcher body
        rect = self.get_bounds()
        pygame.draw.rect(screen, color, rect)
        
        # Draw missile tube (angled upward)
        tube_x = self.position.x + self.width // 2 - 8
        tube_y = self.position.y - 10
        pygame.draw.rect(screen, COLOR_DARK_BLUE, 
                        (tube_x - 3, tube_y - 15, 6, 15))


class Explosion:
    """Explosion effect with expansion and decay phases."""
    
    def __init__(self, x, y, radius=0):
        self.position = pygame.math.Vector2(x, y)
        
        # Start small and expand to max_radius
        if radius > 0:
            self.radius = radius
            self.max_radius = EXPLOSION_MAX_RADIUS
            self.expansion_time = EXPLOSION_EXPANSION_TIME
            self.shrink_time = EXPLOSION_SHRINK_TIME
            self.total_duration = self.expansion_time + self.shrink_time
        else:
            # Instant full explosion
            self.radius = EXPLOSION_MAX_RADIUS
            self.max_radius = EXPLOSION_MAX_RADIUS
            self.expansion_time = 0
            self.shrink_time = EXPLOSION_SHRINK_TIME
            self.total_duration = self.shrink_time
        
        self.is_active = True
        self.start_time = None
    
    def update(self, dt):
        """Update explosion (expand and decay)."""
        if not self.is_active:
            return
        
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
        
        elapsed = (pygame.time.get_ticks() / 1000.0) - self.start_time
        
        if elapsed < self.expansion_time:
            # Expansion phase
            progress = min(1.0, elapsed / self.expansion_time)
            self.radius = self.max_radius * progress
        elif elapsed < self.total_duration:
            # Decay/shrink phase
            decay_progress = (elapsed - self.expansion_time) / self.shrink_time
            self.radius = self.max_radius * (1.0 - decay_progress)
        
        if self.radius <= 0:
            self.is_active = False
