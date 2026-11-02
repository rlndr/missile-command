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
    
    def reset(self):
        """Put the launcher in its ready state for a new game.

        Clears the reload (``cooldown_time`` and ``cooldown_ratio`` to 0.0) and
        brings the launcher back online. Position, size and render offsets are
        left alone. Calling it again changes nothing.
        """
        self.cooldown_time = 0.0
        self.cooldown_ratio = 0.0
        self.is_active = True

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
