"""Score and game statistics tracking."""

import pygame
import json
import os
from game.constants import *


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


class ScoreSystem:
    """Handles scoring and game statistics."""
    
    def __init__(self):
        self.score = 0
        self.buildings_destroyed = 0
        self.total_missiles_hit = 0
        self.time_survived = 0
        
        # Load high score from config if exists
        self.high_score = self.load_high_score()
    
    def load_high_score(self):
        """Load high score from config file."""
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return int(config.get("high_score", 0))
        except (FileNotFoundError, json.JSONDecodeError):
            return 0
    
    def save_high_score(self):
        """Save current score to high score if it's a new high."""
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            new_high = int(config.get("high_score", 0))
            if self.score > new_high:
                config["high_score"] = self.score
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=4)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def add_missile_hit(self, points=10):
        """Add points for missile hit."""
        self.score += points
        self.total_missiles_hit += 1
    
    def add_building_destroyed(self, building):
        """Add points for building destruction."""
        self.score += building.score_value
        self.buildings_destroyed += 1
    
    def add_survival_time(self, dt):
        """Add survival time bonus (1 point per second)."""
        self.score += int(dt * 1)
    
    def reset(self):
        """Reset all scores."""
        self.score = 0
        self.buildings_destroyed = 0
        self.total_missiles_hit = 0
        self.time_survived = 0
    


class ScoreDisplay:
    """Manages on-screen score display."""
    
    def __init__(self, font_size=36):
        self.font = pygame.font.Font(None, font_size)
    
    def draw_score(self, screen, score_system):
        """Draw score at top-right corner."""
        
        # Main score text
        score_text = f"SCORE: {score_system.score:,}"
        text_surface = self.font.render(score_text, True, COLOR_WHITE)
        screen.blit(text_surface, (SCREEN_WIDTH - 200, 10))
        
        # Sub-text with additional stats
        subsurface = self.font.render(
            f"Missiles: {score_system.total_missiles_hit} | Buildings: {score_system.buildings_destroyed}", 
            True, COLOR_GRAY)
        screen.blit(subsurface, (SCREEN_WIDTH - 200, 45))
