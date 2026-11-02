"""Timer and frame management utilities."""

import time


class GameTimer:
    """Handles delta time calculations for game loop."""
    
    def __init__(self):
        self._start_time = time.time()
        self._last_frame_time = self._start_time
    
    def get_delta_time(self):
        """Return delta time since last frame (seconds)."""
        current_time = time.time()
        dt = current_time - self._last_frame_time
        self._last_frame_time = current_time
        return dt if dt >= 0 else 0
    
    def reset(self):
        """Reset timer to current time."""
        self._last_frame_time = time.time()


def get_total_elapsed_time(start_time):
    """Get total time elapsed since game start."""
    return time.time() - start_time
