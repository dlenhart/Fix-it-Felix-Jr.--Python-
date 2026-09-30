import pygame
from constants import (GAME_WIDTH, GAME_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                       RENDER_FPS, TICK_RATE, BLACK, WHITE)
from scene_manager import SceneManager, Scene


class PlaceholderScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont("monospace", 8)

    def draw(self, screen):
        screen.fill(BLACK)
        text = self.font.render("FIX-IT FELIX JR", True, WHITE)
        rect = text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
        screen.blit(text, rect)


def main():
    pygame.init()
    display = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))
    pygame.display.set_caption("Fix-It Felix Jr.")
    clock = pygame.time.Clock()

    # Internal 240x320 surface — all game rendering happens here
    game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

    scene_manager = SceneManager()
    scene_manager.push(PlaceholderScene(scene_manager))

    tick_accumulator = 0.0
    running = True
    while running:
        dt = clock.tick(RENDER_FPS) / 1000.0
        tick_accumulator += dt

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # Fixed-step game logic at 250ms per tick (4 Hz)
        while tick_accumulator >= TICK_RATE:
            scene_manager.tick(None)
            tick_accumulator -= TICK_RATE

        # Render at 60fps to internal surface, then scale up
        scene_manager.draw(game_surface)
        scaled = pygame.transform.scale(game_surface, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        display.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
