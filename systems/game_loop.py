"""Main game class - orchestrates all systems."""

import math
import pygame
import random
from game.constants import *
from entities import (IncomingMissile, DefenseMissile, DefensiveBase, Building)
from entities.terrain import Explosion, ExplosionPool
from utils.timer import GameTimer
from systems.input_system import InputSystem
from systems.score import ScoreSystem


class MainGame:
    """Main game class that manages everything."""
    
    def __init__(self):
        pygame.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Missile Command Clone")
        
        self.clock = pygame.time.Clock()
        self.timer = GameTimer()
        
        self.input_system = InputSystem()
        
        self.state = STATE_START
        
        self.score_system = ScoreSystem()
        
        self.buildings = []
        self.incoming_missiles = []
        self.defense_missiles = []
        self.explosions = []
        
        self.base = DefensiveBase()
        
        self.last_spawn_time = 0
        self.spawn_interval = BASE_SPAWN_INTERVAL
        
        self.explosion_pool = ExplosionPool(pool_size=15)
        
        self.starting_buildings_count = 8
        
        self.game_time = 0.0
        self.shake_intensity = 0
    
    def start_game(self):
        """Initialize game entities at start and ready the launcher to fire."""
        self.buildings = []
        self.incoming_missiles = []
        self.defense_missiles = []
        self.explosions = []
        self.game_time = 0.0
        self.base.reset()

        # Spawn starting buildings along bottom edge
        for i in range(self.starting_buildings_count):
            x = 30 + (i * 80)  # Staggered positions
            y = SCREEN_HEIGHT - 60
            building_type = random.choice(list(BUILDING_TYPES.keys()))
            self.buildings.append(Building(x, y, building_type))
        
        # Reset and track score at game start
        self.score_system.reset()
        self.last_spawn_time = 0.0
        self.shake_intensity = 0
    
    def switch_state(self, new_state):
        """Switch to a different game state."""
        self.state = new_state
        return new_state
    
    def handle_events(self):
        """Process input events and return actions."""
        return self.input_system.handle_events()

    def handle_actions(self, actions):
        """Apply one frame's input ``actions`` (from ``handle_events()``).

        The transition is chosen from the state at the start of the call, so
        at most one state change happens per call. Every entry to
        ``STATE_PLAYING`` resets the frame timer so the first frame back has
        no time jump. Firing only works if play was running before and after.
        """
        state = self.state
        if state in (STATE_START, STATE_GAME_OVER) and "start" in actions:
            self.start_game()
            self.state = STATE_PLAYING
            self.timer.reset()
        elif state == STATE_PLAYING and "toggle_pause" in actions:
            self.state = STATE_PAUSED
        elif state == STATE_PAUSED and "toggle_pause" in actions:
            self.state = STATE_PLAYING
            self.timer.reset()

        if ("fire_missile" in actions and state == STATE_PLAYING
                and self.state == STATE_PLAYING):
            self.spawn_defense_missile(actions["fire_missile"])
    
    def spawn_incoming_missile(self):
        """Spawn an incoming missile from random top position toward a building."""
        standing = [b for b in self.buildings if not b.is_destroyed]
        if standing:
            target_building = random.choice(standing)
            target_point = pygame.math.Vector2(target_building.position.x,
                           SCREEN_HEIGHT - 30 - random.randint(0, 50))
        else:
            target_point = pygame.math.Vector2(random.randint(100, SCREEN_WIDTH - 100), SCREEN_HEIGHT)

        missile = IncomingMissile(target_point)
        self.incoming_missiles.append(missile)
    
    def spawn_new_building(self):
        """Spawn a new random building at a suitable position."""
        building_type = random.choice(list(BUILDING_TYPES.keys()))
        
        available_positions = [
            (random.randint(0, 50), SCREEN_HEIGHT - BUILDING_TYPES[building_type]["height"]),
            (SCREEN_WIDTH - 60 - random.randint(0, 40), SCREEN_HEIGHT - BUILDING_TYPES[building_type]["height"]),
            (random.randint(200, SCREEN_WIDTH - 200), SCREEN_HEIGHT - BUILDING_TYPES[building_type]["height"] + 15),
        ]
        
        if available_positions:
            x, y = random.choice(available_positions)
            building = Building(x, y, building_type)
            self.buildings.append(building)
    
    def spawn_defense_missile(self, target_point):
        """Launch a defense missile to target point."""
        if self.base.can_fire():
            missile = DefenseMissile(pygame.math.Vector2(target_point))
            self.defense_missiles.append(missile)
            self.base.start_cooldown()
    
    def draw_missile(self, missile, color):
        """Draw a missile as a small circle."""
        pygame.draw.circle(self.screen, color,
                          (int(missile.position.x), int(missile.position.y)),
                          missile.radius)
    
    def update(self, dt):
        """Update all game entities."""
        self.game_time += dt
        self.score_system.add_survival_time(dt)

        current_interval = max(MIN_SPAWN_INTERVAL,
                               BASE_SPAWN_INTERVAL / (self.game_time / 60.0 + 1.0))

        if self.game_time - self.last_spawn_time >= current_interval:
            self.spawn_incoming_missile()
            self.last_spawn_time = self.game_time

        self.base.update(dt)

        # Filter destroyed missiles
        self.incoming_missiles = [m for m in self.incoming_missiles
                                  if not m.is_destroyed and m.position.y <= SCREEN_HEIGHT + 50]
        self.defense_missiles = [m for m in self.defense_missiles if not m.is_destroyed]

        # Return expired explosions to pool, keep active ones
        active_explosions = []
        for e in self.explosions:
            if e.is_active:
                active_explosions.append(e)
            else:
                self.explosion_pool.return_explosion(e)
        self.explosions = active_explosions

        for missile in self.incoming_missiles:
            missile.update(dt)

        for missile in self.defense_missiles:
            missile.update(dt)

        # Detonate defense missiles that reached their target this frame.
        for missile in self.defense_missiles:
            if missile.reached_target and not missile.is_destroyed:
                explosion = self.explosion_pool.get_explosion(
                    missile.target.x, missile.target.y, is_player=True)
                self.explosions.append(explosion)
                missile.destroy()

        for explosion in self.explosions:
            explosion.update(dt)

        self.shake_intensity = max(0, self.shake_intensity - dt * SCREEN_SHAKE_DECAY_RATE)
    
    def get_shake_offset(self):
        """Return a random (shake_x, shake_y) offset for the current shake.

        ``shake_intensity`` decays as a float, so the range bound is rounded up
        with ``math.ceil`` to an int before it reaches ``random.randint``. Each
        component is an int in ``[-A, A]`` where ``A = ceil(shake_intensity)``;
        returns ``(0, 0)`` when there is no shake.
        """
        if self.shake_intensity <= 0:
            return (0, 0)
        amplitude = math.ceil(self.shake_intensity)
        return (random.randint(-amplitude, amplitude),
                random.randint(-amplitude, amplitude))

    def hud_score_text(self):
        """Return the in-play HUD score line, e.g. ``"SCORE: 1,234"``."""
        return f"SCORE: {self.score_system.score:,}"

    def draw(self):
        """Render the game frame."""
        
        for y in range(SCREEN_HEIGHT):
            intensity = int(COLOR_BLUE[1] + (y / SCREEN_HEIGHT) * (COLOR_DARK_BLUE[1] - COLOR_BLUE[1]))
            color = (COLOR_BLUE[0], intensity, COLOR_BLUE[2])
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))
        
        shake_x, shake_y = self.get_shake_offset()
        
        self.base.draw_base(self.screen)
        
        sorted_buildings = sorted(self.buildings, key=lambda b: -b.position.y)
        for building in sorted_buildings:
            if not building.is_destroyed:
                building.draw_building(self.screen)
        
        for missile in list(self.defense_missiles):
            self.draw_missile(missile, COLOR_YELLOW)
        
        for missile in list(self.incoming_missiles):
            if not missile.is_destroyed:
                self.draw_missile(missile, COLOR_RED)
        
        for explosion in list(self.explosions):
            if explosion.is_active:
                explosion.draw_explosion(self.screen)

        font = pygame.font.Font(None, 36)
        score_surf = font.render(self.hud_score_text(), True, COLOR_YELLOW)
        score_rect = score_surf.get_rect(topright=(SCREEN_WIDTH - HUD_MARGIN, HUD_MARGIN))
        self.screen.blit(score_surf, score_rect)

        pygame.display.flip()

    def check_collisions(self):
        """Check all collisions and handle damage/effects."""
        
        # Check incoming missiles hitting buildings
        for missile in self.incoming_missiles:
            if missile.is_destroyed:
                continue
            
            for building in self.buildings:
                if not building.is_destroyed:
                    if (missile.position.x >= building.position.x and
                        missile.position.x <= building.position.x + building.width and
                        missile.position.y >= building.position.y and
                        missile.position.y <= building.position.y + building.height):
                        
                        # Building hit!
                        explosion = self.explosion_pool.get_explosion(
                            missile.position.x,
                            missile.position.y
                        )
                        self.explosions.append(explosion)
                        building.take_impact()
                        missile.destroy()
                        self.shake_intensity = SCREEN_SHAKE_BUILDING_HIT
                        break

        # Player explosions destroy incoming missiles inside their current radius
        for explosion in self.explosions:
            if not (explosion.is_active and explosion.is_player):
                continue

            for incoming in self.incoming_missiles:
                if incoming.is_destroyed:
                    continue

                if explosion.position.distance_to(incoming.position) <= explosion.radius:
                    incoming.destroy()
                    self.score_system.add_missile_hit(MISSILE_INTERCEPT_POINTS)
                    self.shake_intensity = SCREEN_SHAKE_INTERCEPT

        # Destroyed buildings drop out of the city.
        self.buildings = [b for b in self.buildings if not b.is_destroyed]

    @property
    def buildings_left(self):
        """Number of buildings in ``self.buildings`` that are not destroyed."""
        return sum(1 for b in self.buildings if not b.is_destroyed)

    def check_game_over(self):
        """End the game and save the high score once when the last building falls.

        Only acts while playing, so it switches to ``STATE_GAME_OVER`` and
        calls ``save_high_score()`` exactly once per game.
        """
        if self.state == STATE_PLAYING and self.buildings_left == 0:
            self.switch_state(STATE_GAME_OVER)
            self.score_system.save_high_score()

    def start_game_loop(self):
        """Run the main loop in the current state until a ``"quit"`` action."""
        clock_delay = 0.16  # Largest dt allowed for one frame

        while True:
            actions = self.handle_events()
            if "quit" in actions:
                break

            self.handle_actions(actions)

            if self.state == STATE_PLAYING:
                dt = min(self.timer.get_delta_time(), clock_delay)
                self.update(dt)
                self.check_collisions()
                self.draw()
                self.check_game_over()
            else:
                self.draw_start_screen()

            self.clock.tick(60)

    
    def menu_lines(self):
        """Return the start or pause screen text as ``(text, font_size, color, centre_y)``.

        Lines are listed top to bottom. Other states return an empty list.
        """
        mid = SCREEN_HEIGHT // 2
        if self.state == STATE_START:
            header = [
                ("Missile Command Clone", 48, COLOR_WHITE, mid - 120),
                ("Defend the city!", 36, COLOR_GRAY, mid - 80),
                (f"High Score: {self.score_system.high_score:,}", 36, COLOR_YELLOW, mid - 30),
            ]
            prompt = "Press SPACE to Start"
        elif self.state == STATE_PAUSED:
            header = [
                ("PAUSED", 48, COLOR_WHITE, mid - 120),
                (f"Score: {self.score_system.score:,}", 36, COLOR_YELLOW, mid - 30),
            ]
            prompt = "Press ESC to Resume"
        else:
            return []
        controls = [
            ("Controls:", 36, COLOR_WHITE, mid + 20),
            ("Mouse Click: Launch defense missile", 36, COLOR_WHITE, mid + 50),
            ("SPACE: Start / Restart", 36, COLOR_WHITE, mid + 80),
            ("ESC: Pause / Resume", 36, COLOR_WHITE, mid + 110),
        ]
        return header + controls + [(prompt, 48, COLOR_YELLOW, mid + 190)]

    def draw_start_screen(self):
        """Draw the start/pause/game over screen."""
        self.screen.fill(COLOR_DARK_BLUE)

        # Darken background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 36)
        
        if self.state == STATE_START or self.state == STATE_PAUSED:
            fonts = {}
            for text, size, color, centre_y in self.menu_lines():
                if size not in fonts:
                    fonts[size] = pygame.font.Font(None, size)
                surf = fonts[size].render(text, True, color)
                self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, centre_y)))

        elif self.state == STATE_GAME_OVER:
            title = font.render("GAME OVER", True, COLOR_RED)
            rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(title, rect)
            
            score_text = small_font.render(f"Final Score: {self.score_system.score:,}", True, COLOR_YELLOW)
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
            self.screen.blit(score_text, score_rect)

            high_text = small_font.render(f"High Score: {self.score_system.high_score:,}", True, COLOR_YELLOW)
            high_rect = high_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
            self.screen.blit(high_text, high_rect)

            restart_text = font.render("Press SPACE to Restart", True, COLOR_WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 110))
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()

    def __del__(self):
        """Cleanup on exit."""
        pygame.quit()

