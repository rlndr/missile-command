"""Player input handling system."""

import pygame


class InputSystem:
    """Manages all player input (keyboard, mouse)."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset input state."""
        self.key_released = {k: False for k in range(256)}  # Track key releases
    
    def handle_events(self):
        """Process pygame events and return actions dict."""
        actions = {}
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions["quit"] = True
            
            elif event.type == pygame.KEYDOWN:
                self.key_released[event.key] = False
                
                if event.key == pygame.K_ESCAPE:
                    actions["pause"] = True
                
                elif event.key == pygame.K_SPACE:
                    actions["start_pause"] = True
            
            elif event.type == pygame.KEYUP:
                self.key_released[event.key] = True
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    actions["fire_missile"] = event.pos
        
        return actions
    
    def get_key_state(self, key):
        """Get current state of a key (pressed/released)."""
        if key in self.key_released:
            released = self.key_released[key]
            
            if isinstance(key, int):
                # Numeric key code - check KEYDOWN events
                pass
            else:
                # Named key like pygame.K_SPACE
                pass
            
            return not released  # Return True if pressed (not released)
        return False
    
    def is_key_held(self, key):
        """Check if a key is currently held down."""
        return not self.key_released.get(key, False)
