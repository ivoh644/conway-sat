import numpy as np

class GameOfLife:
    def __init__(self, width, height, randomize=True):
        self.width = width
        self.height = height
        if randomize:
            self.grid = np.random.choice([0, 1], size=(height, width))
        else:
            self.grid = np.zeros((height, width), dtype=int)

    def step(self):
        """Advance the simulation by one generation."""
        neighbors = sum(
            np.roll(np.roll(self.grid, i, 0), j, 1)
            for i in (-1, 0, 1)
            for j in (-1, 0, 1)
            if (i != 0 or j != 0)
        )
        birth = (neighbors == 3) & (self.grid == 0)
        survive = ((neighbors == 2) | (neighbors == 3)) & (self.grid == 1)
        self.grid[:] = 0
        self.grid[birth | survive] = 1

    def set_pattern(self, pattern, x, y):
        """Place a smaller array pattern at position (x, y)."""
        h, w = pattern.shape
        self.grid[y:y+h, x:x+w] = pattern

    def count_alive(self):
        """Return number of live cells."""
        return np.sum(self.grid)
