"""One floor of the building and its window cells."""

from exe_data.level_table import COLUMN_X, FLOOR_CELL_KINDS, FLOOR_HEIGHT
from world.level_types import FloorType
from world.window_cell import WindowCell


class Floor:
    """One floor of the building, stacked upward in world y."""

    def __init__(self, index: int, floor_type: FloorType, bottom_y: int):
        self.index = index
        self.floor_type = floor_type
        self.bottom_y = bottom_y
        self.height: int = FLOOR_HEIGHT[floor_type]
        self.cells: list[WindowCell] = self._build_cells()

    @property
    def top_y(self) -> int:
        return self.bottom_y - self.height

    def _build_cells(self) -> list[WindowCell]:
        if self.floor_type == FloorType.ROOF:
            return []
        return [
            WindowCell(kind, column, x, self.index)
            for column, (kind, x) in enumerate(
                zip(FLOOR_CELL_KINDS[self.floor_type], COLUMN_X[self.floor_type], strict=True))
        ]
