"""Ralph's drop-hazard timer, shared across the whole game."""

from constants.ralph import RALPH_DROP_DELAY_TICKS, RALPH_POUND_ARRIVALS_PER_DROP


class DropHazardSchedule:
    """When Ralph's pounds request a drop hazard; lasts the whole game.

    [EXE] Only FUN_0040e3f0, at game start, resets DAT_00421740 / DAT_00421744,
    so the count carries across sections and levels, and an armed timer waits
    through walks, rages and level changes until the next pound.
    """

    def __init__(self) -> None:
        self._arrivals_until_drop = RALPH_POUND_ARRIVALS_PER_DROP
        self._timer_ticks = 0

    def on_pound_arrival(self) -> None:
        """FUN_0040d870: every 3rd arrival at a pound spot arms the 30-tick timer."""
        self._arrivals_until_drop -= 1
        if self._arrivals_until_drop != 0:
            return
        self._arrivals_until_drop = RALPH_POUND_ARRIVALS_PER_DROP
        self._timer_ticks = RALPH_DROP_DELAY_TICKS

    def tick_pound(self) -> bool:
        """FUN_0040d970's pound phase: count the timer down; True when it runs out."""
        if self._timer_ticks == 0:
            return False
        self._timer_ticks -= 1
        return self._timer_ticks == 0
