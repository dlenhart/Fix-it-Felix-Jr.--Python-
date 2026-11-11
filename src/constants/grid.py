"""The window grid: five columns per floor, four floors per section."""

COLUMN_COUNT = 5
CENTER_COLUMN = 2
FLOORS_PER_SECTION = 4  # [EXE] FUN_00409610

# The door is the bottom floor's center cell; Felix starts and respawns there too.
DOOR_LOCAL_ROW = 0
DOOR_COLUMN = CENTER_COLUMN
RESPAWN_LOCAL_ROW = 0
RESPAWN_COLUMN = CENTER_COLUMN
