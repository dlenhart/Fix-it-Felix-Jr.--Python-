"""Fixed-step tick rate.

Game logic runs at 60 ticks/sec. The original binary's 250ms SetTimer
(FUN_00413de0) only updates the window title, not game logic (Ghidra pass 3).
60 Hz is inferred from the confirmed timer values: 60 ticks per displayed
second, 1800-tick (30s) high-score entry, etc. At 4 Hz those would be 15s
"seconds" and a 7.5-minute entry timer.
"""

TICKS_PER_SECOND = 60
TICK_RATE = 1.0 / TICKS_PER_SECOND  # seconds per game tick


def seconds_to_ticks(seconds):
    """Convert a real-time duration to a whole number of game ticks."""
    return round(seconds * TICKS_PER_SECOND)
