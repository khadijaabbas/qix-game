import sys

TEST_MODE = "--test" in sys.argv

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    if TEST_MODE:
        import types

        class _Vector2:
            def __init__(self, x=0, y=0):
                self.x = x
                self.y = y
            def rotate_rad(self, angle):
                return _Vector2(self.x, self.y)

        class _Surface:
            def __init__(self, *args, **kwargs):
                pass
            def fill(self, *args, **kwargs):
                pass
            def blit(self, *args, **kwargs):
                pass
            def set_alpha(self, *args, **kwargs):
                pass

        def _rect_factory(*args, **kwargs):
            class _Rect:
                def __init__(self, *args, **kwargs):
                    pass
                def collidepoint(self, *args, **kwargs):
                    return False
            return _Rect()

        pygame = types.SimpleNamespace(
            init=lambda: None,
            quit=lambda: None,
            time=types.SimpleNamespace(get_ticks=lambda: 0),
            display=types.SimpleNamespace(set_mode=lambda *args, **kwargs: _Surface(), set_caption=lambda *args, **kwargs: None),
            Surface=_Surface,
            SRCALPHA=0,
            font=types.SimpleNamespace(Font=lambda *args, **kwargs: type("F", (), {"render": lambda *a, **k: None})()),
            draw=types.SimpleNamespace(circle=lambda *a, **k: None,
                                       polygon=lambda *a, **k: None,
                                       rect=lambda *a, **k: None,
                                       lines=lambda *a, **k: None,
                                       line=lambda *a, **k: None),
            event=types.SimpleNamespace(get=lambda: []),
            key=types.SimpleNamespace(get_pressed=lambda: []),
            K_LEFT=0,
            K_RIGHT=0,
            K_UP=0,
            K_DOWN=0,
            K_SPACE=0,
            K_RETURN=0,
            K_ESCAPE=0,
            QUIT=0,
            math=types.SimpleNamespace(Vector2=_Vector2),
            Rect=_rect_factory
        )
        sys.modules["pygame"] = pygame
    else:
        raise

from main_header import *
import random

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FIELD_MARGIN = 50

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Qix Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.level = 1
        self.game_state = "START"
        self.world = None
        self.player = None
        self.qix = None
        self.sparcs = []
        self.target_percentage = 12.5
        
    def _init_level(self):
        field_width = WINDOW_WIDTH - 2 * FIELD_MARGIN
        field_height = WINDOW_HEIGHT - 2 * FIELD_MARGIN - 50
        
        self.world = World(FIELD_MARGIN, FIELD_MARGIN, field_width, field_height)
        
        start_x = FIELD_MARGIN
        start_y = FIELD_MARGIN
        self.player = Player(start_x, start_y, self.world)
        
        center_x = FIELD_MARGIN + field_width * 3 // 4
        center_y = FIELD_MARGIN + field_height * 3 // 4
        self.qix = Qix(center_x, center_y, self.world)
        
        num_sparcs = 1 if self.level <= 2 else 2
        self.sparcs = []
        right_edge_x = FIELD_MARGIN + field_width
        bottom_edge_y = FIELD_MARGIN + field_height
        vertical_spacing = max(1, field_height // (num_sparcs + 1))
        for i in range(num_sparcs):
            sparc_y = bottom_edge_y - i * vertical_spacing
            direction = 1 if i == 0 else -1
            self.sparcs.append(Sparc(right_edge_x, sparc_y, self.world, direction=direction))
        
        self.target_percentage = min(12.5 * self.level, 62.5)
        qix_base_speed = 1.5
        qix_increment = 0.25
        self.qix.speed = qix_base_speed + (self.level - 1) * qix_increment
        self.qix.reset_motion()
        
        sparc_base_speed = 1.4
        sparc_increment = 0.15
        for sparc in self.sparcs:
            sparc.speed = sparc_base_speed + (self.level - 1) * sparc_increment
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if self.game_state == "START":
                        self.level = 1
                        self._init_level()
                        self.game_state = "PLAYING"
                    elif self.game_state == "PLAYING":
                        self.game_state = "PAUSED"
                    elif self.game_state == "PAUSED":
                        self.game_state = "PLAYING"
                    elif self.game_state == "LEVEL_COMPLETE":
                        self.level += 1
                        self._init_level()
                        self.game_state = "PLAYING"
                    elif self.game_state == "GAME_OVER":
                        self.level = 1
                        self._init_level()
                        self.game_state = "PLAYING"
                elif event.key == pygame.K_SPACE and self.game_state == "PLAYING":
                    self.player.start_push()
                elif event.key == pygame.K_ESCAPE and self.game_state in {"LEVEL_COMPLETE", "GAME_OVER", "PAUSED"}:
                    return False
        return True
    
    def update(self):
        if self.game_state != "PLAYING" or not self.world:
            return
        
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        
        if keys[pygame.K_LEFT]:
            dx = -1
        elif keys[pygame.K_RIGHT]:
            dx = 1
        
        if dx == 0:
            if keys[pygame.K_UP]:
                dy = -1
            elif keys[pygame.K_DOWN]:
                dy = 1
        
        if dx != 0 or dy != 0:
            qix_pos = self.qix.get_position()
            self.player.move(dx, dy, qix_pos)
        
        self.qix.update()
        for sparc in self.sparcs:
            sparc.update()
        
        player_x, player_y = self.player.get_position()
        
        if self.player.is_pushing:
            qix_x, qix_y = self.qix.get_position()
            
            if self.qix.check_collision(player_x, player_y, threshold=15):
                self.player.cancel_push()
            elif self.world.check_incursion_collision(qix_x, qix_y, threshold=15):
                self.player.cancel_push()
            else:
                for sparc in self.sparcs:
                    sparc_x, sparc_y = sparc.get_position()
                    if sparc.check_collision(player_x, player_y, threshold=10):
                        self.player.cancel_push()
                        break
                    elif self.world.check_incursion_collision(sparc_x, sparc_y, threshold=10):
                        self.player.cancel_push()
                        break
        else:
            for sparc in self.sparcs:
                if sparc.check_collision(player_x, player_y, threshold=10):
                    if self.player.lose_life():
                        self.player.reset_position()
                    break
        
        self.player.check_push_idle()
        
        if not self.player.is_alive():
            self.game_state = "GAME_OVER"
        
        claimed_percentage = self.world.get_claimed_percentage()
        if claimed_percentage >= self.target_percentage:
            self.game_state = "LEVEL_COMPLETE"
    
    def draw(self):
        self.screen.fill((255, 255, 255))
        
        if self.game_state == "START":
            self._draw_start_screen()
            pygame.display.flip()
            return
        
        if not self.world:
            pygame.display.flip()
            return
        
        self.world.draw(self.screen)
        
        self.player.draw(self.screen)
        self.qix.draw(self.screen)
        for sparc in self.sparcs:
            sparc.draw(self.screen)
        
        lives_text = self.small_font.render(f"Lives: {self.player.lives}", True, (0, 0, 0))
        self.screen.blit(lives_text, (10, 10))
        
        claimed_percentage = self.world.get_claimed_percentage()
        claimed_text = self.small_font.render(f"{claimed_percentage:.1f}% claimed", True, (0, 0, 0))
        self.screen.blit(claimed_text, (10, WINDOW_HEIGHT - 40))
        
        level_text = self.small_font.render(
            f"Level {self.level} - {self.target_percentage}% needed", 
            True, (0, 0, 0)
        )
        text_rect = level_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30))
        self.screen.blit(level_text, text_rect)
        
        if self.game_state == "LEVEL_COMPLETE":
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            title_text = self.font.render("Level Complete!", True, (0, 255, 0))
            title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50))
            self.screen.blit(title_text, title_rect)
            
            continue_text = self.small_font.render("Press ENTER to continue", True, (255, 255, 255))
            continue_rect = continue_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
            self.screen.blit(continue_text, continue_rect)
            
            quit_text = self.small_font.render("Press ESC to quit", True, (255, 255, 255))
            quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
            self.screen.blit(quit_text, quit_rect)
        
        elif self.game_state == "GAME_OVER":
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            title_text = self.font.render("Game Over!", True, (255, 0, 0))
            title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50))
            self.screen.blit(title_text, title_rect)
            
            restart_text = self.small_font.render("Press ENTER to restart", True, (255, 255, 255))
            restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
            self.screen.blit(restart_text, restart_rect)
            
            quit_text = self.small_font.render("Press ESC to quit", True, (255, 255, 255))
            quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
            self.screen.blit(quit_text, quit_rect)
        elif self.game_state == "PAUSED":
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(160)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            paused_text = self.font.render("Paused", True, (255, 255, 0))
            paused_rect = paused_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
            self.screen.blit(paused_text, paused_rect)
            
            resume_text = self.small_font.render("Press ENTER to resume", True, (255, 255, 255))
            resume_rect = resume_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
            self.screen.blit(resume_text, resume_rect)

            quit_text = self.small_font.render("Press ESC to quit", True, (255, 255, 255))
            quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
            self.screen.blit(quit_text, quit_rect)
        
        pygame.display.flip()
    
    def _draw_start_screen(self):
        title_text = self.font.render("Qix Game", True, (0, 0, 0))
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(title_text, title_rect)
        
        prompt_text = self.small_font.render("Press ENTER to start", True, (0, 0, 0))
        prompt_rect = prompt_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        self.screen.blit(prompt_text, prompt_rect)
        
        pause_text = self.small_font.render("Press ENTER during play to pause/resume", True, (0, 0, 0))
        pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
        self.screen.blit(pause_text, pause_rect)
        
        control_text = self.small_font.render("Arrow keys move, SPACE to start an incursion.", True, (0, 0, 0))
        control_rect = control_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
        self.screen.blit(control_text, control_rect)
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()

def run_tests():
    def new_player():
        world = World(0, 0, 100, 100)
        player = Player(world.x, world.y, world)
        player.x = world.x
        player.y = world.y
        player.last_edge_pos = (player.x, player.y)
        world.start_incursion(player.x, player.y)
        player.is_pushing = True
        player.push_start_pos = (player.x, player.y)
        player.last_push_move_time = 0
        return player
    
    # First move must leave the edge
    player = new_player()
    assert not player.move(1, 0), "Cannot move along edge while in incursion"
    assert player.move(0, 1), "Should be able to enter the field"

    # Backtracking blocked on single axis
    player = new_player()
    assert player.move(0, 1)
    initial = player.get_position()
    assert not player.move(0, -1)
    assert player.get_position() == initial
    assert player.move(1, 0)
    after_turn = player.get_position()
    assert not player.move(-1, 0)
    assert player.get_position() == after_turn
    assert player.move(0, 1)
    
    # Turning unlocks new axis while blocking opposite
    player = new_player()
    assert player.move(0, 1)
    assert player.move(1, 0)
    assert not player.move(-1, 0)
    assert player.move(0, -1)
    
    # Idle timeout costs a life and cancels push
    player = new_player()
    player.lives = 3
    player.check_push_idle(current_time=1600)
    assert player.lives == 2
    assert not player.is_pushing
    assert player.get_position() == player.last_edge_pos
    
    print("All gameplay tests passed.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    else:
        game = Game()
        game.run()
