"""Terrain and explosion system."""

import math
import pygame
from game.constants import *


def explosion_settings(is_building=False, is_ground=False):
    """Return ``(max_radius, expansion_time, shrink_time)`` for an explosion type."""
    if is_building:
        return (BUILDING_EXPLOSION_MAX_RADIUS, BUILDING_EXPLOSION_EXPANSION_TIME,
                BUILDING_EXPLOSION_SHRINK_TIME)
    if is_ground:
        return (GROUND_IMPACT_MAX_RADIUS, GROUND_IMPACT_EXPANSION_TIME,
                GROUND_IMPACT_SHRINK_TIME)
    return (EXPLOSION_MAX_RADIUS, EXPLOSION_EXPANSION_TIME, EXPLOSION_SHRINK_TIME)


class Explosion:
    """Explosion effect that grows then shrinks over game time.

    The radius grows from 0 to ``max_radius`` over ``expansion_time``
    seconds, shrinks back to 0 over ``shrink_time`` seconds, then the
    explosion goes inactive. Age is accumulated from ``dt`` in ``elapsed``,
    so it follows game time. ``is_player`` marks explosions from defense
    missiles, which destroy incoming missiles. ``is_building`` marks the
    larger, fiery fireball spawned when a building is destroyed.
    ``is_ground`` marks the small, harmless ring blast left where an enemy
    missile hits the ground; it uses the ``GROUND_IMPACT_*`` size and timings.
    """

    def __init__(self, x, y, is_player=False, is_building=False, is_ground=False):
        self.position = pygame.math.Vector2(x, y)
        self.is_player = is_player
        self.is_building = is_building
        self.is_ground = is_ground
        self.radius = 0
        self.max_radius, self.expansion_time, self.shrink_time = explosion_settings(
            is_building, is_ground)
        self.elapsed = 0.0
        self.is_active = True

    def update(self, dt):
        """Advance the explosion by ``dt`` seconds and recompute its radius."""
        if not self.is_active:
            return

        self.elapsed += dt

        if self.elapsed < self.expansion_time:
            self.radius = self.max_radius * self.elapsed / self.expansion_time
        elif self.elapsed < self.expansion_time + self.shrink_time:
            shrink_progress = (self.elapsed - self.expansion_time) / self.shrink_time
            self.radius = self.max_radius * (1.0 - shrink_progress)
        else:
            self.radius = 0
            self.is_active = False

    def fade_alpha(self):
        """Return the 0..255 opacity for a building explosion at its current age."""
        if not self.is_active or self.radius <= 0:
            return 0
        if self.elapsed <= self.expansion_time:
            return 255
        if self.elapsed < self.expansion_time + self.shrink_time:
            shrink_progress = (self.elapsed - self.expansion_time) / self.shrink_time
            return max(0, min(255, round(255 * (1.0 - shrink_progress))))
        return 0

    def fire_layers(self):
        """Return ``[(layer_radius, color), ...]`` from outer to inner for a building blast.

        Radii are modulated deterministically from ``self.elapsed`` so paused
        frames never flicker.
        """
        if not self.is_active or self.radius <= 0:
            return []
        layers = []
        for i, (scale, color) in enumerate(BUILDING_EXPLOSION_LAYERS):
            flicker = 1.0 + BUILDING_EXPLOSION_FLICKER_AMOUNT * math.sin(
                self.elapsed * BUILDING_EXPLOSION_FLICKER_SPEED + i * 2.0
            )
            layer_radius = max(0, round(self.radius * scale * flicker))
            layers.append((layer_radius, color))
        return layers

    def draw_explosion(self, screen):
        """Draw the explosion with visual effects."""
        if not self.is_active:
            return

        if self.is_building:
            layers = self.fire_layers()
            alpha = self.fade_alpha()
            if not layers or alpha <= 0:
                return
            max_r = max(r for r, _ in layers)
            if max_r <= 0:
                return
            size = max_r * 2 + 1
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            centre = (max_r, max_r)
            for layer_radius, color in layers:
                if layer_radius > 0:
                    pygame.draw.circle(surf, (*color, alpha), centre, layer_radius)
            screen.blit(surf, (int(self.position.x) - max_r, int(self.position.y) - max_r))
            return

        # Draw fading rings
        ring_spacing = 3

        for ring in range(4):
            ring_offset = ring * ring_spacing
            ring_radius = max(0, self.radius - ring_offset)

            # Create gradient from center outward
            color_intensity = 255 - (ring * 60)
            color = (min(255, color_intensity),
                     min(200, color_intensity),
                     50 + (ring * 30))

            pygame.draw.circle(screen, color,
                             (int(self.position.x), int(self.position.y)),
                             ring_radius)


class ExplosionPool:
    """Object pooling for explosions."""

    def __init__(self, pool_size=10):
        self.pool_size = pool_size
        self.explosion_pool = []

        # Pre-create explosion objects
        for _ in range(pool_size):
            exp = Explosion(400, 300)
            exp.is_active = False
            self.explosion_pool.append(exp)

    def get_explosion(self, x, y, is_player=False, is_building=False, is_ground=False):
        """Get a fresh explosion at ``(x, y)``, reusing a pooled one if available.

        Every per-use field is reset on a reused object so nothing carries
        over from its previous life.
        """
        if self.explosion_pool:
            exp = self.explosion_pool.pop()
            exp.position.update(x, y)
            exp.is_player = is_player
            exp.is_building = is_building
            exp.is_ground = is_ground
            exp.radius = 0
            exp.max_radius, exp.expansion_time, exp.shrink_time = explosion_settings(
                is_building, is_ground)
            exp.elapsed = 0.0
            exp.is_active = True
            return exp
        return Explosion(x, y, is_player, is_building, is_ground)

    def return_explosion(self, explosion):
        """Return a used explosion to the pool."""
        explosion.is_active = False
        self.explosion_pool.append(explosion)
