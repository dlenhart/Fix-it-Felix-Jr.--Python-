"""Screen geometry, render rate and colours."""

# Internal game resolution (confirmed by Ghidra: 240x320 portrait)
GAME_WIDTH = 240
GAME_HEIGHT = 320

# Display scaling
DISPLAY_SCALE = 3
DISPLAY_WIDTH = GAME_WIDTH * DISPLAY_SCALE   # 720
DISPLAY_HEIGHT = GAME_HEIGHT * DISPLAY_SCALE  # 960

RENDER_FPS = 60  # Display refresh rate

BLACK = (0, 0, 0)
SKY_BLUE = (92, 148, 252)

TEXT_SIDE_MARGIN = 8  # screen text scaled to fit keeps this gap at both edges
SCREEN_CENTER = (GAME_WIDTH // 2, GAME_HEIGHT // 2)
