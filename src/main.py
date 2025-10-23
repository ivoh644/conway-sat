from game_of_life import GameOfLife
import time
import os

def display(grid):
    """Print the grid to the console."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print('\n'.join(''.join('⬛' if c else '⬜' for c in row) for row in grid))

if __name__ == "__main__":
    game = GameOfLife(20, 20, randomize=True)

    for step in range(100):
        display(game.grid)
        game.step()
        time.sleep(0.2)
