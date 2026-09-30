"""Interactive sprite atlas viewer for identifying bounding boxes.

Usage: python3 tools/sprite_viewer.py [palette_number]

Controls:
  - Click and drag to select a region
  - Mouse wheel to zoom in/out
  - Arrow keys to pan
  - P + number to switch palette (0-4)
  - H to switch to hammer sheets
  - Escape to quit

Prints (x, y, w, h) of selected region to stdout.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame
from constants import ASSET_DIR

pygame.init()

VIEWER_WIDTH = 1200
VIEWER_HEIGHT = 900

screen = pygame.display.set_mode((VIEWER_WIDTH, VIEWER_HEIGHT))
pygame.display.set_caption("Sprite Atlas Viewer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 14)

palette = int(sys.argv[1]) if len(sys.argv) > 1 else 0
showing_hammer = False


def load_atlas():
    if showing_hammer:
        path = os.path.join(ASSET_DIR, f"hammer{palette}.png")
    else:
        path = os.path.join(ASSET_DIR, f"felix{palette}.png")
    return pygame.image.load(path).convert_alpha()


atlas = load_atlas()
zoom = 1.0
pan_x, pan_y = 0, 0
drag_start = None
drag_end = None
selected_rect = None

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_h:
                showing_hammer = not showing_hammer
                atlas = load_atlas()
            elif event.key in (pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                palette = event.key - pygame.K_0
                atlas = load_atlas()
            elif event.key == pygame.K_LEFT:
                pan_x += 50
            elif event.key == pygame.K_RIGHT:
                pan_x -= 50
            elif event.key == pygame.K_UP:
                pan_y += 50
            elif event.key == pygame.K_DOWN:
                pan_y -= 50
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                drag_start = event.pos
                drag_end = event.pos
            elif event.button == 4:
                zoom = min(zoom * 1.2, 8.0)
            elif event.button == 5:
                zoom = max(zoom / 1.2, 0.25)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and drag_start:
                drag_end = event.pos
                sx = int((min(drag_start[0], drag_end[0]) - pan_x) / zoom)
                sy = int((min(drag_start[1], drag_end[1]) - pan_y) / zoom)
                ex = int((max(drag_start[0], drag_end[0]) - pan_x) / zoom)
                ey = int((max(drag_start[1], drag_end[1]) - pan_y) / zoom)
                w = ex - sx
                h = ey - sy
                if w > 2 and h > 2:
                    selected_rect = (sx, sy, w, h)
                    print(f"({sx}, {sy}, {w}, {h}),")
                drag_start = None
        elif event.type == pygame.MOUSEMOTION:
            if drag_start:
                drag_end = event.pos

    screen.fill((40, 40, 40))

    scaled = pygame.transform.scale(atlas, (int(1024 * zoom), int(1024 * zoom)))
    screen.blit(scaled, (pan_x, pan_y))

    if drag_start and drag_end:
        rect = pygame.Rect(
            min(drag_start[0], drag_end[0]),
            min(drag_start[1], drag_end[1]),
            abs(drag_end[0] - drag_start[0]),
            abs(drag_end[1] - drag_start[1]),
        )
        pygame.draw.rect(screen, (255, 255, 0), rect, 2)
        sx = int((rect.x - pan_x) / zoom)
        sy = int((rect.y - pan_y) / zoom)
        sw = int(rect.w / zoom)
        sh = int(rect.h / zoom)
        info = font.render(f"({sx}, {sy}, {sw}, {sh})", True, (255, 255, 0))
        screen.blit(info, (rect.x, rect.y - 18))

    if selected_rect:
        sx, sy, sw, sh = selected_rect
        draw_rect = pygame.Rect(
            int(sx * zoom + pan_x), int(sy * zoom + pan_y),
            int(sw * zoom), int(sh * zoom)
        )
        pygame.draw.rect(screen, (0, 255, 0), draw_rect, 2)

    mx, my = pygame.mouse.get_pos()
    atlas_x = int((mx - pan_x) / zoom)
    atlas_y = int((my - pan_y) / zoom)
    coords = font.render(f"Atlas: ({atlas_x}, {atlas_y})  Zoom: {zoom:.1f}x  Palette: {palette}  {'HAMMER' if showing_hammer else 'FELIX'}", True, (255, 255, 255))
    screen.blit(coords, (10, VIEWER_HEIGHT - 24))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
