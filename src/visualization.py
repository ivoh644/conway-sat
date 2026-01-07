import pygame
import numpy as np
import os
import datetime
from matplotlib import cm

from game_of_life import GameOfLife
from sat_solver import solve_initial_for_target, solve_initial_minimal_iterative

CELL = 12
FPS = 15
TOP = 50
GRID_COLOR = (0, 0, 0)
DEAD = (255, 255, 255)

viridis = cm.get_cmap("viridis", 9)


class Visualizer:
    def __init__(self, w=50, h=50):
        pygame.init()
        self.game = GameOfLife(w, h, randomize=True)
        self.screen = pygame.display.set_mode((w * CELL, h * CELL + TOP))
        pygame.display.set_caption("Game of Life (clean + informative)")
        self.clock = pygame.time.Clock()
        self.paused = False

        self.font = pygame.font.SysFont("Arial", 14)
        self.save_btn = pygame.Rect(10, 10, 80, 30)
        self.load_btn = pygame.Rect(100, 10, 90, 30)
        self.loading = False
        self.config_files = []

    # ---------- helpers ----------

    def neighbors(self):
        return sum(
            np.roll(np.roll(self.game.grid, i, 0), j, 1)
            for i in (-1, 0, 1)
            for j in (-1, 0, 1)
            if (i, j) != (0, 0)
        )

    # ---------- IO ----------

    def save_config(self):
        path = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(path, exist_ok=True)

        name = datetime.datetime.now().strftime("config_%Y%m%d_%H%M%S.npz")
        np.savez_compressed(os.path.join(path, name), grid=self.game.grid)
        print("💾 Saved", name)

    def _scan_configs(self):
        path = os.path.join(os.path.dirname(__file__), "..", "data")
        if not os.path.isdir(path):
            return []
        return sorted(
            f for f in os.listdir(path)
            if f.startswith("config_") and f.endswith(".npz")
        )

    
    def open_load_menu(self):
        self.config_files = self._scan_configs()
        if not self.config_files:
            print("⚠️ No saved configs found.")
            return
        self.loading = True
    # ---------- drawing ----------

    def draw(self):
        if self.loading:
            # solid background when menu is open
            self.screen.fill((240, 240, 240))
        else:
            self.screen.fill(DEAD)
            neigh = self.neighbors()

            for y in range(self.game.height):
                for x in range(self.game.width):
                    if self.game.grid[y, x]:
                        rgba = viridis(neigh[y, x] / 8.0)
                        color = tuple(int(255 * c) for c in rgba[:3])
                    else:
                        color = DEAD

                    pygame.draw.rect(
                        self.screen,
                        color,
                        (x * CELL, y * CELL + TOP, CELL, CELL),
                    )

            # grid lines
            for x in range(self.game.width + 1):
                pygame.draw.line(
                    self.screen, GRID_COLOR,
                    (x * CELL, TOP),
                    (x * CELL, TOP + self.game.height * CELL), 1
                )
            for y in range(self.game.height + 1):
                pygame.draw.line(
                    self.screen, GRID_COLOR,
                    (0, y * CELL + TOP),
                    (self.game.width * CELL, y * CELL + TOP), 1
                )

        # buttons (still visible)
        pygame.draw.rect(self.screen, (200, 255, 200), self.save_btn)
        pygame.draw.rect(self.screen, (200, 220, 255), self.load_btn)
        self.screen.blit(self.font.render("Save", True, (0, 0, 0)), (28, 18))
        self.screen.blit(self.font.render("Load", True, (0, 0, 0)), (118, 18))

        
    def draw_load_menu(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((240, 240, 240, 240))
        self.screen.blit(overlay, (0, 0))

        title = self.font.render("Select configuration to load", True, (0, 0, 0))
        self.screen.blit(title, (20, 15))

        for i, name in enumerate(self.config_files):
            y = 50 + i * 24
            rect = pygame.Rect(20, y, 360, 22)

            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(self.screen, (200, 220, 255), rect)
            else:
                pygame.draw.rect(self.screen, (220, 220, 220), rect)

            label = self.font.render(name, True, (0, 0, 0))
            self.screen.blit(label, (rect.x + 5, rect.y + 3))
    # ---------- events ----------

    def handle(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False

            # ---------------- LOADING MODE ----------------
            if self.loading:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.loading = False

                if e.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    idx = (my - 50) // 24

                    if 0 <= idx < len(self.config_files):
                        path = os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "data",
                            self.config_files[idx],
                        )
                        data = np.load(path)
                        self.game.grid = data["grid"].copy()
                        self.paused = True
                        self.loading = False
                        print(f"📂 Loaded {self.config_files[idx]}")

                continue  # ⬅️ IMPORTANT: skip normal handling

            # ---------------- NORMAL MODE ----------------
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    self.paused = not self.paused

                elif e.key == pygame.K_b:
                    print("🧠 Backward solve requested")
                    print(f"   steps = 6")
                    print(f"   live cells in target = {int(self.game.grid.sum())}")

                    sol = solve_initial_minimal_iterative(
                        self.game.grid,
                        steps=1,
                        start_bound=500,
                        timeout_ms=60000
                    )

                    if sol is not None:
                        print("✅ Solution applied to grid")
                        self.game.grid = sol
                        self.paused = True
                    else:
                        print("❌ No solution found")
                        
                elif e.key == pygame.K_c:
                    print("🧹 Clearing board")
                    self.game.grid[:] = 0
                    self.paused = True
                
                elif e.key == pygame.K_RIGHT:
                    print("➡️ Stepping forward one generation")
                    self.game.step()
                    self.paused = True

            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if self.save_btn.collidepoint(mx, my):
                    self.save_config()

                elif self.load_btn.collidepoint(mx, my):
                    self.open_load_menu()

                else:
                    gx, gy = mx // CELL, (my - TOP) // CELL
                    if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
                        self.game.grid[gy, gx] ^= 1

        return True

    # ---------- loop ----------

    def run(self):
        running = True
        while running:
            running = self.handle()

            if not self.paused and not self.loading:
                self.game.step()

            self.draw()

            if self.loading:
                self.draw_load_menu()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    Visualizer().run()
