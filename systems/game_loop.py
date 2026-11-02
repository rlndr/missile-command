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
        self.base_cooldown = 0.0
        
        self.last_spawn_time = 0
        self.spawn_interval = BASE_SPAWN_INTERVAL
        
        self.explosion_pool = ExplosionPool(pool_size=15)
        
        self.starting_buildings_count = 8
        
        self.game_time = 0.0
        self.total_missile_hits_this_level = 0
        self.shake_intensity = 0
    
    def start_game(self):
        """Initialize game entities at start."""
        self.buildings = []
        self.incoming_missiles = []
        self.defense_missiles = []
        self.explosions = []
        self.game_time = 0.0

        # Spawn starting buildings along bottom edge
        for i in range(self.starting_buildings_count):
            x = 30 + (i * 80)  # Staggered positions
            y = SCREEN_HEIGHT - 60
            building_type = random.choice(list(BUILDING_TYPES.keys()))
            self.buildings.append(Building(x, y, building_type))
        
        # Reset and track score at game start
        self.score_system.reset()
        self.last_spawn_time = pygame.time.get_ticks() / 1000.0
    
    def switch_state(self, new_state):
        """Switch to a different game state."""
        self.state = new_state
        return new_state
    
    def handle_events(self):
        """Process input events and return actions."""
        return self.input_system.handle_events()
    
    def spawn_incoming_missile(self):
        """Spawn an incoming missile from random top position toward a building."""
        if self.buildings:
            target_building = random.choice(self.buildings)
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

        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_spawn_time >= current_interval:
            self.spawn_incoming_missile()
            self.last_spawn_time = current_time

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
        score_surf = font.render(f"SCORE: {self.score_system.score:,}", True, COLOR_YELLOW)
        self.screen.blit(score_surf, (SCREEN_WIDTH - 220, 10))

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
                            missile.position.y,
                            30
                        )
                        self.explosions.append(explosion)
                        building.take_damage(building.damage_threshold * 25)
                        missile.destroy()
                        self.shake_intensity = SCREEN_SHAKE_BUILDING_HIT
        
        # Check defense missiles hitting incoming missiles
        for missile in self.defense_missiles:
            if missile.is_destroyed:
                continue
            
            for incoming in self.incoming_missiles:
                if incoming.is_destroyed:
                    continue
                
                if (missile.position.x >= incoming.position.x and
                    missile.position.x <= incoming.position.x + 16 and
                    missile.position.y >= incoming.position.y and
                    missile.position.y <= incoming.position.y + 16):
                    
                    explosion = self.explosion_pool.get_explosion(
                        missile.position.x,
                        missile.position.y,
                        50
                    )
                    self.explosions.append(explosion)
                    missile.destroy()
                    incoming.destroy()
                    self.shake_intensity = SCREEN_SHAKE_INTERCEPT
        
        # Check building vs explosion collisions
        for building in self.buildings:
            if building.is_destroyed:
                continue
            
            for explosion in list(self.explosions):
                if not explosion.is_active:
                    continue
                
                # Calculate actual distance from explosion center to building position
                distance = (explosion.position - building.position).length()
                
                # Damage is highest at center, decreases with distance
                damage = max(0, EXPLOSION_MAX_RADIUS - distance)
                building.take_damage(min(damage * 25, building.damage_threshold * 15))


    def handle_score_updates(self):
        """Update score from various sources."""
        
        if self.total_missile_hits_this_level > 0:
            self.score_system.add_missile_hit(10)
        
        dt = self.timer.get_delta_time()
        self.score_system.add_survival_time(dt)
        
        if self.total_missile_hits_this_level == 0:
            self.total_missile_hits_this_level = 1
        
        elapsed = pygame.time.get_ticks() / 1000.0 - self.last_spawn_time
        self.game_time += dt
    
    def start_game_loop(self):
        """Start the main game loop."""
        
        self.state = STATE_PLAYING
        self.start_game()
        self.total_missile_hits_this_level = 0
        
        running = True
        clock_delay = 0.16  # ~60 FPS target
        
        while running:
            actions = self.handle_events()
            
            if "quit" in actions:
                running = False
            
            elif "start_pause" in actions and self.state == STATE_PLAYING:
                self.state = STATE_START
                
                for building in self.buildings:
                    if not building.is_destroyed:
                        self.buildings.remove(building)
            
            elif "resume" in actions:
                self.state = STATE_PLAYING
                self.total_missile_hits_this_level = 0
            
            elif "pause" in actions and self.state == STATE_PLAYING:
                self.state = STATE_PAUSED
            
            elif "fire_missile" in actions:
                self.spawn_defense_missile(actions["fire_missile"])
            
            # Check for restart after game over (spacebar press when in game over state)
            if self.state == STATE_GAME_OVER and "start_pause" in actions:
                # Restart the game with fresh buildings and reset score
                self.start_game()
                self.score_system.reset()
                self.total_missile_hits_this_level = 0
                self.last_spawn_time = pygame.time.get_ticks() / 1000.0
            elif self.state == STATE_GAME_OVER:
                # Try to save high score at end of session
                self.score_system.save_high_score()
            
            if self.state == STATE_PLAYING:
                dt = min(self.timer.get_delta_time(), clock_delay)
                self.update(dt)
                self.check_collisions()
                self.draw()

                if not self.buildings and self.state != STATE_GAME_OVER:
                    self.switch_state(STATE_GAME_OVER)
            else:
                self.draw_start_screen()

            self.clock.tick(60)

    
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
            if self.state == STATE_START:
                title = "Missile Command Clone"
                subtitle = "Defend the city!"
            else:  # PAUSED
                title = "PAUSED"
                subtitle = ""
            
            title_text = font.render(title, True, COLOR_WHITE)
            rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
            self.screen.blit(title_text, rect)
            
            subtitle_text = small_font.render(subtitle, True, COLOR_GRAY)
            if subtitle_text:
                subrect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
                self.screen.blit(subtitle_text, subrect)
            
            controls = [
                "Controls:",
                f"Mouse Click: Launch defense missile",
                "SPACE: Start/Pause game",
                "ESC: Pause/Resume",
            ]
            
            y_offset = SCREEN_HEIGHT // 2 + 50
            for line in controls:
                text = small_font.render(line, True, COLOR_WHITE)
                rect = text.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                self.screen.blit(text, rect)
                y_offset += 30
            
            score_info = font.render("Score", True, COLOR_YELLOW)
            score_text = small_font.render(f"{self.score_system.score:,}", True, COLOR_WHITE)
            score_rect = score_info.get_rect(center=(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 40))
            self.screen.blit(score_info, score_rect)
            self.screen.blit(score_text, (score_rect.x + 120, score_rect.y))
            
            high_score = small_font.render("High Score", True, COLOR_GRAY)
            score_value = small_font.render(str(self.score_system.high_score), True, COLOR_GRAY)
            hsr = high_score.get_rect(center=(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(high_score, hsr)
            self.screen.blit(score_value, (hsr.x + 120, hsr.y))
        
        elif self.state == STATE_GAME_OVER:
            title = font.render("GAME OVER", True, COLOR_RED)
            rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(title, rect)
            
            score_text = small_font.render(f"Final Score: {self.score_system.score:,}", True, COLOR_YELLOW)
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
            self.screen.blit(score_text, score_rect)
            
            restart_text = font.render("Press SPACE to Restart", True, COLOR_WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()

    def __del__(self):
        """Cleanup on exit."""
        pygame.quit()

