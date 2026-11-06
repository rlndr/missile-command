"""Missile entities - incoming and defense missiles."""

import pygame
import random
from collections import deque
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

        # Past positions, oldest first; the deque drops the oldest past the cap
        self.trail = deque(maxlen=ENEMY_TRAIL_MAX_POINTS)

    def update(self, dt):
        """Record a trail sample, then move the missile.

        A copy of the current position is added to ``trail`` before moving
        when the trail is empty or the missile is at least
        ``ENEMY_TRAIL_SPACING`` px past the newest sample. A destroyed missile
        records nothing and does not move.
        """
        if not self.is_destroyed and (
                not self.trail
                or self.position.distance_to(self.trail[-1]) >= ENEMY_TRAIL_SPACING):
            self.trail.append(pygame.math.Vector2(self.position))

        super().apply_velocity(dt)

        # Mark as destroyed if off screen (bottom edge)
        if self.position.y > SCREEN_HEIGHT + 50:
            self.destroy()

    def trail_segments(self):
        """Return the trail as ``(start, end, color)`` tuples, head first.

        Segment 0 runs from the head to the newest sample and segment k from
        ``trail[-k]`` to ``trail[-1-k]``. Colours blend linearly per channel
        from ``ENEMY_TRAIL_HEAD_COLOR`` (segment 0) to
        ``ENEMY_TRAIL_TAIL_COLOR`` (last segment). Empty trail gives ``[]``.
        """
        n = len(self.trail)
        points = [self.position] + list(reversed(self.trail))
        segments = []
        for k in range(n):
            f = k / (n - 1) if n > 1 else 0.0
            color = tuple(
                max(0, min(255, round(head + (tail - head) * f)))
                for head, tail in zip(ENEMY_TRAIL_HEAD_COLOR, ENEMY_TRAIL_TAIL_COLOR))
            segments.append((pygame.math.Vector2(points[k]),
                             pygame.math.Vector2(points[k + 1]), color))
        return segments

    def draw_trail(self, screen):
        """Draw the trail on ``screen``, oldest segment first, without the head."""
        for start, end, color in reversed(self.trail_segments()):
            pygame.draw.line(screen, color, start, end, ENEMY_TRAIL_WIDTH)

class DefenseMissile(GameEntity):
    """Player-controlled defensive missile.

    Flies in a straight line from the launcher to the clicked target at a
    constant speed, stops exactly on the target and sets ``reached_target``
    so the game can detonate it there.
    """

    def __init__(self, target_point):
        super().__init__(LAUNCHER_X_OFFSET, LAUNCHER_Y_OFFSET)
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
