import pygame
from constants import (GAME_WIDTH, GAME_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                       RENDER_FPS, TICK_RATE, BLACK, WHITE)
from scene_manager import SceneManager, Scene
from input_handler import InputHandler, Action
from scenes.title_scene import TitleScene


def main():
    pygame.init()
    display = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))
    pygame.display.set_caption("Fix-It Felix Jr.")
    clock = pygame.time.Clock()

    # Internal 240x320 surface — all game rendering happens here
    game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

    scene_manager = SceneManager()
    scene_manager.push(TitleScene(scene_manager))

    input_handler = InputHandler()

    tick_accumulator = 0.0
    running = True
    while running:
        dt = clock.tick(RENDER_FPS) / 1000.0
        tick_accumulator += dt

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        input_handler.poll(events)
        if input_handler.is_just_pressed(Action.QUIT):
            running = False

        # Fixed-step game logic at TICKS_PER_SECOND (60 Hz)
        while tick_accumulator >= TICK_RATE:
            scene_manager.tick(input_handler)
            input_handler.consume_just_pressed()
            tick_accumulator -= TICK_RATE

        pygame.display.set_caption(f"Fix-It Felix Jr.")

        # How far we are into the next pending tick (0..1) — lets entities
        # interpolate their rendered position so motion stays smooth when
        # render frames and logic ticks drift out of step.
        alpha = tick_accumulator / TICK_RATE

        # Render at 60fps to internal surface, then scale up
        scene_manager.draw(game_surface, alpha)
        scaled = pygame.transform.scale(game_surface, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        display.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
