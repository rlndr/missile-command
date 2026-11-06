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
    """Player-controlled defensive missile.

    Flies in a straight line from the launcher's muzzle to the clicked
    target at a constant speed, stops exactly on the target and sets
    ``reached_target`` so the game can detonate it there.
    """

    def __init__(self, target_point):
        super().__init__(LAUNCHER_X, LAUNCHER_Y)
        self.target = pygame.math.Vector2(target_point.x, target_point.y)
        self.speed = DEFENSE_MISSILE_SPEED
        self.radius = 5
        self.reached_target = False

        # Velocity is fixed for the whole flight. A zero-length shot (target
        # on the launcher) gets zero velocity instead of normalising a zero
        # vector, which pygame rejects; update() then arrives at once.
        offset = self.target - self.position
        if offset.length_squared() > 0:
            self.velocity = offset.normalize() * self.speed
        else:
            self.velocity = pygame.math.Vector2(0, 0)

    def update(self, dt):
        """Step toward the target, snapping onto it when this step would reach it."""
        if self.reached_target or self.is_destroyed:
            return

        remaining = self.target.distance_to(self.position)
        if remaining <= self.speed * dt:
            self.position = pygame.math.Vector2(self.target)
            self.reached_target = True
        else:
            super().apply_velocity(dt)
