from typing import NamedTuple


class Size(NamedTuple):
    x: int
    y: int

    def __eq__(self, value) -> bool:
        if not isinstance(value, Size):
            return False
        (x, y) = value
        return self.x == x and self.y == y

    def __hash__(self):
        return hash((self.x, self.y))
