"""Building entities - destructible city structures."""

import pygame
from game.constants import *
from . import GameEntity


class Building(GameEntity):
    """A city building that takes damage from explosions."""
    
    def __init__(self, x, y, building_type="residential"):
        super().__init__(x, y)
        
        config = BUILDING_TYPES.get(building_type, BUILDING_TYPES["residential"])
        
        self.building_type = building_type
        self.health_max = config["health_max"]
        self.health_current = self.health_max
        self.score_value = config["score_value"]
        self.damage_threshold = config["damage_threshold"]
        
        self.width = config["width"]
        self.height = config["height"]
        self.color = config["color"]
        
        # Visual offset for rendering
        self.render_offset_x = -self.width // 2 + x
        self.render_offset_y = -self.height // 2 + y
    
    @property
    def health(self):
        """Current health normalized (0.0 to 1.0)."""
        return self.health_current / max(self.health_max, 1)
    
    def take_damage(self, damage_amount):
        """Apply damage to building."""
        self.health_current -= damage_amount
        
        if self.health_current <= 0:
            self.health_current = 0
            self.destroy()
    
    def get_bounds(self):
        """Get rectangular bounds for collision detection."""
        return pygame.Rect(
            self.position.x,
            self.position.y,
            self.width,
            self.height
        )
    
    def is_health_depleted(self):
        """Check if building health has reached critical state."""
        return self.health_current <= (self.health_max * 0.3)
    
    def draw_building(self, screen, color=None):
        """Draw building with optional damage visualization."""
        
        # Main building body
        x = self.position.x
        y = self.position.y
        w = self.width
        h = self.height
        
        if color:
            fill_color = color
        else:
            fill_color = self.color
        
        # Draw building rectangle with border
        pygame.draw.rect(screen, COLOR_DARK_BLUE, 
                        (x - 1, y - 1, w + 2, h + 2), 2)
        pygame.draw.rect(screen, fill_color, (x, y, w, h))
        
        # Add windows (visual detail)
        window_width = 4
        window_height = 3
        spacing = self.width // 6
        
        for row in range(h // 8):
            for col in range(w // 10):
                win_x = x + 2 + col * spacing
                win_y = y + 2 + row * 5
                pygame.draw.rect(screen, COLOR_WHITE if self.health > 0.7 else 
                               (100, 200, 100), (win_x, win_y, window_width, window_height))
        
        # Damage indicator lines when health is low
        if self.is_health_depleted():
            damage_lines = [
                (x + w * 0.3, y + h * 0.2, 4, 1, self.color),
                (x + w * 0.5, y + h * 0.7, 6, 1, COLOR_RED),
            ]
            for pos_x, pos_y, length, width, dmg_color in damage_lines:
                pygame.draw.line(screen, dmg_color, 
                               (pos_x, pos_y), 
                               (pos_x + length, pos_y), width)
        
        # Health bar when damaged significantly
        if self.health < 1.0 and self.health > 0.5:
            bar_width = w - 8
            bar_height = 6
            bar_x = x + 2
            bar_y = y - 4
            
            # Background
            pygame.draw.rect(screen, COLOR_BLACK, (bar_x, bar_y, bar_width, bar_height))
            
            # Health fill
            health_fill_width = int(bar_width * self.health)
            pygame.draw.rect(screen, 
                           (255 if self.health > 0.7 else 
                            150 if self.health > 0.4 else 50),
                           (bar_x, bar_y, health_fill_width, bar_height))
