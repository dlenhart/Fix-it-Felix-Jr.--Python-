"""The high-score table and initials entry."""

MAX_SCORES = 5  # [EXE] 5 entries
INITIALS_LENGTH = 3  # [EXE] 3 characters
# [EXE] 38 characters including space, A-Z, 0-9, period.
LETTER_OPTIONS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
# [EXE] FUN_00408fc0 case 8 starts the entry on "A" (index 1, after the space), and
# FUN_00407f50 puts each next slot back on index 1 when a letter is confirmed.
FIRST_LETTER_INDEX = 1
# [EXE] FUN_00408280 draws the entry's letters in font row 1 (red) and flashes the
# current one to row 0 (white) while (frame counter & 0x1f) >= 0xf: 15 ticks red,
# then 17 white.
INITIALS_COLOR_ROW = 1
CURRENT_LETTER_FLASH_COLOR_ROW = 0
CURRENT_LETTER_FLASH_PERIOD_MASK = 0x1F
CURRENT_LETTER_FLASH_START_TICK = 0xF

HS_DISPLAY_TIMER_TICKS = 900  # 15 seconds
# TODO: parked (user, 2026-10-30): the exe's initials entry has a 30 s TIME LEFT
# limit (1800 ticks) plus hold-to-repeat every 20 ticks; not wired up yet.
HS_ENTRY_TIMER_TICKS = 1800  # [EXE] 30 displayed seconds

# [EXE] FUN_0040a060 seeds the table with these names (string table 0x419e68) and
# scores; both the scores and the names are from the exe.
DEFAULT_HIGH_SCORES = (
    ("VAV", 15000),
    ("DES", 10000),
    ("RYS", 8000),
    ("KYL", 6000),
    ("CMI", 4000),
)
