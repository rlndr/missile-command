"""Terrain and explosion system."""

import pygame
from game.constants import *


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
    
    def get_explosion(self, x, y, radius=0):
        """Get a reusable explosion instance."""
        if self.explosion_pool:
            exp = self.explosion_pool.pop()
            exp.position.update(x, y)
            exp.radius = radius if radius > 0 else EXPLOSION_MAX_RADIUS
            exp.max_radius = EXPLOSION_MAX_RADIUS
            exp.expansion_time = EXPLOSION_EXPANSION_TIME if radius > 0 else 0
            exp.shrink_time = EXPLOSION_SHRINK_TIME
            exp.total_duration = exp.expansion_time + exp.shrink_time
            exp.is_active = True
            exp.start_time = None
            return exp
        return Explosion(x, y, radius)
    
    def return_explosion(self, explosion):
        """Return a used explosion to the pool."""
        explosion.is_active = False
        self.explosion_pool.append(explosion)
