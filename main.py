"""Main entry point for Missile Command Clone."""

import pygame
from systems.game_loop import MainGame


def main():
    """Entry point for the game."""
    
    # Initialize Pygame (done in MainGame.__init__)
    game = MainGame()
    
    # Run game loop
    game.start_game_loop()
    
    # Cleanup handled by __del__ when game is garbage collected
    return game


if __name__ == "__main__":
    main()
