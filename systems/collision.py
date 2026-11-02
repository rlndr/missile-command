"""Collision detection and damage handling."""

import pygame
from utils.vector_math import check_circle_collision


class CollisionSystem:
    """Handles all collision detection and damage calculations."""
    
    @staticmethod
    def missile_to_missile_collision(incoming, defense):
        """Detect collision between two missiles."""
        return check_circle_collision(
            incoming.position, 8,
            defense.position, 5
        )
    
    @staticmethod
    def missile_to_building_collision(missile, building):
        """Detect missile hitting a building."""
        # Check if missile is within building bounds
        rect = building.get_bounds()
        return (rect.x <= missile.position.x <= rect.x + rect.width and
                rect.y <= missile.position.y <= rect.y + rect.height)
    
    @staticmethod
    def missile_to_base_collision(missile, base):
        """Detect missile hitting the launcher base."""
        rect = base.get_bounds()
        return (rect.x <= missile.position.x <= rect.x + rect.width and
                rect.y <= missile.position.y <= rect.y + rect.height)
    
    @staticmethod
    def building_to_building_collision(building1, building2):
        """Check collision between two buildings."""
        bounds1 = building1.get_bounds()
        bounds2 = building2.get_bounds()
        return bounds1.colliderect(bounds2)
    
    @staticmethod
    def missile_in_explosion(missile, explosion):
        """Check if missile is within explosion damage radius."""
        distance = (missile.position - explosion.position).length()
        return distance <= explosion.radius
    
    @staticmethod
    def building_in_explosion(building, explosion):
        """Check if building is within explosion damage radius."""
        distance = (building.position - explosion.position).length()
        return distance <= explosion.radius
    
    @staticmethod
    def building_to_explosion(building, explosion):
        """Determine overlap between building and explosion."""
        building_rect = building.get_bounds()
        explosion_center = pygame.math.Vector2(explosion.position)
        
        # Closest point on rect to center
        closest_x = max(building_rect.x, min(explosion.position.x, building_rect.right))
        closest_y = max(building_rect.y, min(explosion.position.y, building_rect.bottom))
        
        distance = ((explosion.position.x - closest_x) ** 2 + 
                    (explosion.position.y - closest_y) ** 2) ** 0.5
        
        return distance <= explosion.radius
