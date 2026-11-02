"""Game entities - base classes and exports."""

import pygame
from game.constants import *


class GameEntity:
    """Base class for all game entities."""
    
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.is_destroyed = False
    
    def apply_velocity(self, dt):
        """Apply velocity for the given delta time."""
        if not self.is_destroyed:
            self.position += self.velocity * dt
    
    def is_active(self):
        """Check if entity is active (not destroyed)."""
        return not self.is_destroyed
    
    def destroy(self):
        """Mark entity as destroyed."""
        self.is_destroyed = True


from .missile import IncomingMissile, DefenseMissile
from .base import DefensiveBase, Explosion
from .building import Building


__all__ = [
    'GameEntity',
    'IncomingMissile',
    'DefenseMissile',
    'DefensiveBase',
    'Explosion',
    'Building',
]
