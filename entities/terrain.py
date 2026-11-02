"""Terrain and explosion system."""

import pygame
from game.constants import *


class Explosion:
    """Explosion effect that grows then shrinks over game time.

    The radius grows from 0 to ``max_radius`` over
    ``EXPLOSION_EXPANSION_TIME`` seconds, shrinks back to 0 over
    ``EXPLOSION_SHRINK_TIME`` seconds, then the explosion goes inactive.
    Age is accumulated from ``dt`` in ``elapsed``, so it follows game time.
    ``is_player`` marks explosions from defense missiles, which destroy
    incoming missiles.
    """

    def __init__(self, x, y, is_player=False):
        self.position = pygame.math.Vector2(x, y)
        self.is_player = is_player
        self.radius = 0
        self.max_radius = EXPLOSION_MAX_RADIUS
        self.elapsed = 0.0
        self.is_active = True

    def update(self, dt):
        """Advance the explosion by ``dt`` seconds and recompute its radius."""
        if not self.is_active:
            return

        self.elapsed += dt

        if self.elapsed < EXPLOSION_EXPANSION_TIME:
            self.radius = self.max_radius * self.elapsed / EXPLOSION_EXPANSION_TIME
        elif self.elapsed < EXPLOSION_EXPANSION_TIME + EXPLOSION_SHRINK_TIME:
            shrink_progress = (self.elapsed - EXPLOSION_EXPANSION_TIME) / EXPLOSION_SHRINK_TIME
            self.radius = self.max_radius * (1.0 - shrink_progress)
        else:
            self.radius = 0
            self.is_active = False

    def draw_explosion(self, screen):
        """Draw the explosion with visual effects."""
        if not self.is_active:
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
    
    def get_explosion(self, x, y, is_player=False):
        """Get a fresh explosion at ``(x, y)``, reusing a pooled one if available.

        Every per-use field is reset on a reused object so nothing carries
        over from its previous life.
        """
        if self.explosion_pool:
            exp = self.explosion_pool.pop()
            exp.position.update(x, y)
            exp.is_player = is_player
            exp.radius = 0
            exp.max_radius = EXPLOSION_MAX_RADIUS
            exp.elapsed = 0.0
            exp.is_active = True
            return exp
        return Explosion(x, y, is_player)

    def return_explosion(self, explosion):
        """Return a used explosion to the pool."""
        explosion.is_active = False
        self.explosion_pool.append(explosion)
