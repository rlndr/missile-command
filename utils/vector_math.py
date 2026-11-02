"""Utility functions for vector math and timing."""

import pygame
from pygame.math import Vector2


def get_distance(pos1, pos2):
    """Calculate distance between two positions."""
    v = Vector2(pos2) - Vector2(pos1)
    return v.length()


def check_circle_collision(pos1, radius1, pos2, radius2):
    """Check if two circles collide."""
    return get_distance(pos1, pos2) <= (radius1 + radius2)


def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def interpolate(start, end, factor):
    """Linear interpolation: start + (end - start) * factor."""
    return start + (end - start) * factor


