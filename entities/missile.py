"""Missile entities - incoming and defense missiles."""

import pygame
import random
from game.constants import *
from . import GameEntity


class IncomingMissile(GameEntity):
    """Enemy missile traveling from sky toward city."""

    def __init__(self, target_point):
        super().__init__(random.randint(50, SCREEN_WIDTH - 50), -50)
        self.target = pygame.math.Vector2(target_point.x, target_point.y + 50)
        self.speed = INCOMING_MISSILE_SPEED
        self.radius = 8
        
        # Calculate velocity vector to reach target
        direction = (self.target - self.position).normalize()
        self.velocity = direction * self.speed
    
    def update(self, dt):
        """Update missile position."""
        super().apply_velocity(dt)
        
        # Mark as destroyed if off screen (bottom edge)
        if self.position.y > SCREEN_HEIGHT + 50:
            self.destroy()

class DefenseMissile(GameEntity):
    """Player-controlled defensive missile with curved trajectory."""
    
    def __init__(self, target_point):
        super().__init__(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)
        self.target = pygame.math.Vector2(target_point.x, target_point.y)
        self.speed = DEFENSE_MISSILE_SPEED
        self.radius = 5

        dx = self.target.x - self.position.x
        dy = self.target.y - self.position.y
        distance = (dx**2 + dy**2) ** 0.5

        if distance > 0:
            direction = pygame.math.Vector2(dx, dy).normalize()
        else:
            direction = pygame.math.Vector2(0, 1)

        self.velocity = direction * self.speed
    
    def update(self, dt):
        """Update missile position and trajectory."""
        super().apply_velocity(dt)
        
        # Calculate new target point ahead of current position (for turning)
        lookahead_distance = 20
        # Use current velocity direction for lookahead
        if self.velocity.x > 0:
            direction_of_flight_sign = 1
        else:
            direction_of_flight_sign = -1
        
        new_target = pygame.math.Vector2(
            self.position.x + direction_of_flight_sign * lookahead_distance,
            self.target.y
        )
        
        # Recalculate direction based on new target
        direction_to_target = (new_target - self.position).normalize()
        
        # Smoothly interpolate velocity toward new direction
        desired_velocity = direction_to_target * self.speed
        self.velocity = self.velocity.lerp(desired_velocity, 0.1)


