"""Defensive base launcher."""

import pygame
from game.constants import *
from entities import GameEntity


class DefensiveBase(GameEntity):
    """Player's missile launcher: a tower on the ground at the bottom centre.

    The tower is a body standing on the ground strip with a thin barrel on
    top. Defense missiles leave from the muzzle, the top centre of the barrel.
    """
    
    def __init__(self):
        """Build the tower with its muzzle at ``(LAUNCHER_X, LAUNCHER_Y)``.

        ``position`` is the muzzle (the launch point). ``width`` and ``height``
        are the body's size, and the render offsets go from the muzzle to the
        body's upper-left corner, so ``get_bounds()`` returns the body, which
        stands on the ground.
        """
        super().__init__(LAUNCHER_X, LAUNCHER_Y)
        
        self.cooldown_time = BASE_COOLDOWN_TIME
        self.cooldown_length = BASE_COOLDOWN_TIME
        self.rapid_fire = False
        self.is_active = True
        self.width = LAUNCHER_WIDTH
        self.height = LAUNCHER_HEIGHT
        
        # Offset from the muzzle to the body's upper-left corner
        self.render_offset_x = -LAUNCHER_WIDTH // 2
        self.render_offset_y = LAUNCHER_BARREL_HEIGHT
    
    def reset(self):
        """Put the launcher in its ready state for a new game.

        Clears the reload (``cooldown_time`` and ``cooldown_ratio`` to 0.0),
        turns rapid fire off (``cooldown_length`` back to
        ``BASE_COOLDOWN_TIME``) and brings the launcher back online. Position,
        size and render offsets are left alone. Calling it again changes
        nothing.
        """
        self.cooldown_time = 0.0
        self.cooldown_ratio = 0.0
        self.cooldown_length = BASE_COOLDOWN_TIME
        self.rapid_fire = False
        self.is_active = True

    def set_rapid_fire(self, on):
        """Turn the rapid-fire reload on or off.

        Switching on cuts a reload that has longer than
        ``RAPID_FIRE_COOLDOWN_TIME`` left down to that, so a slow reload
        doesn't eat into the window. Switching off lets the running reload
        finish as it is.
        """
        switching_on = bool(on) and not self.rapid_fire
        self.rapid_fire = bool(on)
        if switching_on and self.cooldown_time > RAPID_FIRE_COOLDOWN_TIME:
            self.cooldown_time = RAPID_FIRE_COOLDOWN_TIME
            self.cooldown_length = RAPID_FIRE_COOLDOWN_TIME

    def can_fire(self):
        """Check if base can fire another missile."""
        return self.is_active and self.cooldown_time <= 0
    
    def start_cooldown(self):
        """Start the reload after firing: short while rapid fire is on, else normal."""
        if self.is_active:
            if self.rapid_fire:
                self.cooldown_length = RAPID_FIRE_COOLDOWN_TIME
            else:
                self.cooldown_length = BASE_COOLDOWN_TIME
            self.cooldown_time = self.cooldown_length
    
    def update(self, dt):
        """Update cooldown timer."""
        if not self.is_active:
            return
        
        self.cooldown_time = max(0, self.cooldown_time - dt)
        
        # Visual indicator for cooldown
        self.cooldown_ratio = min(1.0, self.cooldown_time / self.cooldown_length)
    
    def reload_progress(self):
        """Return how far the reload has got, from 0.0 (just fired) to 1.0 (ready).

        Worked out from ``cooldown_time`` and the length of the current reload
        (``cooldown_length``) on every call, so it is never stale
        (unlike ``cooldown_ratio``). Clamped to ``[0.0, 1.0]``. Returns 0.0 when
        the launcher is offline, so the bar never looks ready while
        ``can_fire()`` is False.
        """
        if not self.is_active:
            return 0.0
        progress = 1.0 - self.cooldown_time / self.cooldown_length
        return max(0.0, min(1.0, progress))

    def cooldown_bar_rects(self):
        """Return ``(track_rect, fill_rect)`` for the reload bar under the launcher.

        The track is the launcher's width, ``COOLDOWN_BAR_HEIGHT`` tall and
        ``COOLDOWN_BAR_GAP`` px below its bounds. The fill shares the track's
        left, top and height; its width is rounded down so it is only full
        when the reload is done.
        """
        bounds = self.get_bounds()
        track = pygame.Rect(bounds.left, bounds.bottom + COOLDOWN_BAR_GAP,
                            self.width, COOLDOWN_BAR_HEIGHT)
        fill = pygame.Rect(track.left, track.top,
                           int(track.width * self.reload_progress()), track.height)
        return track, fill

    def get_bounds(self):
        """Get rectangular bounds for collision detection."""
        return pygame.Rect(
            self.position.x + self.render_offset_x,
            self.position.y + self.render_offset_y,
            self.width,
            self.height
        )
    
    def barrel_rect(self):
        """Return the barrel's rect, centred on the muzzle with its bottom on the body's top."""
        return pygame.Rect(
            self.position.x - LAUNCHER_BARREL_WIDTH // 2,
            self.position.y,
            LAUNCHER_BARREL_WIDTH,
            LAUNCHER_BARREL_HEIGHT
        )

    def draw_base(self, screen, active_color=COLOR_WHITE, inactive_color=COLOR_GRAY):
        """Draw the tower body, its barrel in the same colour and the reload bar under it.

        While active with rapid fire on, the body and barrel use
        ``LAUNCHER_RAPID_FIRE_COLOR`` instead of ``active_color``.
        """
        
        if not self.is_active:
            color = inactive_color
            # Add visual indicator that base is offline
            pygame.draw.rect(screen, COLOR_RED, self.get_bounds(), 3)
        elif self.rapid_fire:
            color = LAUNCHER_RAPID_FIRE_COLOR
        else:
            color = active_color
        
        # Draw main launcher body
        rect = self.get_bounds()
        pygame.draw.rect(screen, color, rect)
        
        # Draw the barrel on top of the body
        pygame.draw.rect(screen, color, self.barrel_rect())

        # Draw the reload bar: the track, then the fill on top of it
        track, fill = self.cooldown_bar_rects()
        pygame.draw.rect(screen, COOLDOWN_BAR_TRACK_COLOR, track)
        if fill.width > 0:
            fill_color = COOLDOWN_BAR_READY_COLOR if self.can_fire() else COOLDOWN_BAR_FILL_COLOR
            pygame.draw.rect(screen, fill_color, fill)
