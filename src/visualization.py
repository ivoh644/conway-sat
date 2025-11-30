import pygame
import numpy as np
from game_of_life import GameOfLife
from matplotlib import cm  # colormap for viridis
from sat_solver import solve_initial_for_target, solve_backward_components
import time
import os
import datetime
import matplotlib.pyplot as plt

CELL_SIZE = 12
FPS = 15
GRID_COLOR = (0, 0, 0)       # black grid
DEAD_COLOR = (255, 255, 255) # white background
UI_MARGIN = 60
TOP_MARGIN = 60

# Use the viridis colormap from Matplotlib
viridis = cm.get_cmap("viridis", 9)

class GameOfLifeVisualizer:
    def __init__(self, width=50, height=50):
        pygame.init()
        self.game = GameOfLife(width, height, randomize=True)
        self.screen = pygame.display.set_mode((width * CELL_SIZE, height * CELL_SIZE + UI_MARGIN))
        pygame.display.set_caption("Conway's Game of Life – Step Mode Enabled")
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False   # space toggles this
        self.step_once = False  # right arrow triggers a single step
        self.selection_start = None
        self.selection_end = None
        self.selection_active = False
        self.initial_declared_state = None
        self.back_steps = 0
        self.button_rect = pygame.Rect(10, 10, 70, 30)
        self.button_color = (200, 220, 255)
        self.button_text_color = (0, 0, 0)
        self.font = pygame.font.SysFont("Arial", 12)
        self.load_button_rect = pygame.Rect(90, 10, 70, 30)
        self.load_button_color = (220, 240, 255)
        self.initial_declared_state = None
        self.back_steps = 0            # how far we are from the initial
        self.reconstruction_phase = 0  # the "target backward layer" we’re working on
        self.initial_chain = []



    def save_session(self):
        """Save the current grid, initial state, and metadata into ../data."""
        # Determine the path relative to this file (not working dir)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "..", "data")
        os.makedirs(data_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(data_dir, f"session_{timestamp}.npz")

        np.savez_compressed(
            filename,
            current_grid=self.game.grid,
            initial_state=self.initial_declared_state
            if self.initial_declared_state is not None
            else np.zeros_like(self.game.grid),
            back_steps=self.back_steps,
            initial_chain=getattr(self, "initial_chain", [])
        )

        print(f"💾 Saved session to {os.path.abspath(filename)}")

    def compute_neighbors(self):
        """Compute number of live neighbors for each cell."""
        return sum(
            np.roll(np.roll(self.game.grid, i, 0), j, 1)
            for i in (-1, 0, 1)
            for j in (-1, 0, 1)
            if (i != 0 or j != 0)
        )
    
    def check_backsolve_consistency(self):
        if self.initial_declared_state is None or self.back_steps == 0:
            return
        temp_game = GameOfLife(self.game.width, self.game.height, randomize=False)
        temp_game.grid = self.game.grid.copy()
        for _ in range(self.back_steps):
            temp_game.step()
        if consistent := np.array_equal(temp_game.grid, self.initial_declared_state):
            print(f"✅ Chain consistent after {self.back_steps} backward steps.")
        else:
            print(f"❌ Chain inconsistency detected at step {self.back_steps}.")

    def snap_to_grid(self, pos):
        x, y = pos
        grid_x = (x // CELL_SIZE) * CELL_SIZE
        grid_y = (y // CELL_SIZE) * CELL_SIZE
        return grid_x, grid_y
    
    def draw_grid(self):
        y_offset = 60
        self.screen.fill(DEAD_COLOR)
        grid = self.game.grid
        neighbors = self.compute_neighbors()

        for y in range(self.game.height):
            for x in range(self.game.width):
                if grid[y, x] == 1:
                    n = neighbors[y, x]
                    rgba = viridis(n / 8.0)
                    color = tuple(int(255 * c) for c in rgba[:3])
                else:
                    color = DEAD_COLOR
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE +y_offset, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, color, rect)

        # Grid lines
        for x in range(self.game.width + 1):
            pygame.draw.line(
                self.screen,
                GRID_COLOR,
                (x * CELL_SIZE, TOP_MARGIN),
                (x * CELL_SIZE, TOP_MARGIN + self.game.height * CELL_SIZE),
                1
            )
        for y in range(self.game.height + 1):
            pygame.draw.line(
                self.screen,
                GRID_COLOR,
                (0, y * CELL_SIZE + TOP_MARGIN),
                (self.game.width * CELL_SIZE, y * CELL_SIZE + TOP_MARGIN),
                1
            )

        if self.selection_active and self.selection_start and self.selection_end:
            self._draw_selection_box()

        pygame.draw.rect(self.screen, self.button_color, self.button_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 80), self.button_rect, 2, border_radius=8)
        label = self.font.render("Declare Initial", True, self.button_text_color)
        self.screen.blit(label, (self.button_rect.x+10, self.button_rect.y+10))
        
        pygame.draw.rect(self.screen, self.load_button_color, self.load_button_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 80), self.load_button_rect, 2, border_radius=8)
        load_label = self.font.render("Load Initial", True, (0, 0, 0))
        self.screen.blit(load_label, (self.load_button_rect.x + 10, self.load_button_rect.y + 10))

        pygame.display.flip()

    def _draw_selection_box(self):
        x0, y0 = self.selection_start
        x1, y1 = self.selection_end
        rect = pygame.Rect(
            min(x0, x1),
            min(y0, y1),
            abs(x1 - x0) + CELL_SIZE,
            abs(y1 - y0) + CELL_SIZE
        )
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((230, 230, 230, 100))  # translucent light gray
        self.screen.blit(s, rect)
        pygame.draw.rect(self.screen, (180, 180, 180), rect, 2)

    def _handle_editor_quit_event(self):
        pygame.quit()
        return False, False # running, quit_pygame_flag

    def _confirm_initial_state(self, editor_grid):
        self.initial_declared_state = editor_grid.copy()
        self.back_steps = 0
        self.button_color = (150, 255, 150)
        print("✅ Declared new initial state.")
        return False # Set running to False

    def open_initial_editor(self):
        """Opens a new grid editor screen to declare the initial state."""
        print("🧩 Opening initial state editor...")

        editor_grid = np.zeros_like(self.game.grid, dtype=int)
        running = True

        # Define buttons
        confirm_rect = pygame.Rect(10, 10, 40, 20)
        cancel_rect = pygame.Rect(60, 10, 40, 20)
        font = pygame.font.SysFont("Arial", 11)

        while running:
            self.screen.fill((255, 255, 255))

            # --- Draw editable grid ---
            for y in range(self.game.height):
                for x in range(self.game.width):
                    rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE+ TOP_MARGIN, CELL_SIZE, CELL_SIZE)
                    color = (50, 180, 80) if editor_grid[y, x] else (255, 255, 255)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, (220, 220, 220), rect, 1)

            # --- Buttons ---
            pygame.draw.rect(self.screen, (170, 255, 170), confirm_rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 170, 170), cancel_rect, border_radius=8)
            self.screen.blit(font.render("Confirm", True, (0, 0, 0)), (confirm_rect.x + 4, confirm_rect.y + 3))
            self.screen.blit(font.render("Cancel", True, (0, 0, 0)), (cancel_rect.x + 4, cancel_rect.y + 3))

            pygame.display.flip()

            # --- Handle events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running, _ = self._handle_editor_quit_event()
                    return

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()

                    if confirm_rect.collidepoint(mx, my):
                        running = self._confirm_initial_state(editor_grid)
                        return

                    elif cancel_rect.collidepoint(mx, my):
                        print("❌ Cancelled initial declaration.")
                        running = False
                        return

                    else:
                        # Toggle a cell
                        gx = mx // CELL_SIZE
                        gy = (my-TOP_MARGIN) // CELL_SIZE
                        if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
                            editor_grid[gy, gx] = 1 - editor_grid[gy, gx]

    def toggle_cell(self, mouse_pos):
        """Toggle a cell with mouse click."""
        x, y = mouse_pos
        grid_x = x // CELL_SIZE
        grid_y = y // CELL_SIZE

        if 0 <= grid_x < self.game.width and 0 <= grid_y < self.game.height:
            self.game.grid[grid_y, grid_x] = 1 - self.game.grid[grid_y, grid_x]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("👋 Window closed. Saving session...")
                self.save_session()
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.game = GameOfLife(self.game.width, self.game.height, randomize=True)
                    self.selection_start = self.selection_end = None
                    self.selection_active = False
                elif event.key == pygame.K_c:
                    self.game.grid[:] = 0
                    self.selection_start = self.selection_end = None
                    self.selection_active = False
                elif event.key == pygame.K_RIGHT:
                    self.game.step()
                    

                elif event.key == pygame.K_b:
                    # Handle selection-aware backsolve
                    target = self.game.grid.copy()
                    if self.selection_active:
                        print("🔍 Solving for previous step within selection box...")
                        #bisection to find least max_ones that works
                        min_ones = 1
                        max_ones = 500
                        successful_init = None
                        while min_ones < max_ones:
                            mid_ones = (min_ones + max_ones) // 2
                            # solve_selection_backwards now returns the solution grid or None
                            current_init = self.solve_selection_backwards(target, max_ones=mid_ones)
                            if current_init is not None:
                                max_ones = mid_ones
                                successful_init = current_init # Store the successful init
                            else:
                                min_ones = mid_ones + 1
                        # After bisection, try one last time with min_ones to get the actual solution
                        final_init = self.solve_selection_backwards(target, max_ones=min_ones)
                        if final_init is not None:
                            self.game.grid = final_init
                            self.back_steps += 1
                            print(f"⬅️ Global reconstruction advanced to step -{self.back_steps}.")
                            self.draw_grid(); pygame.display.flip()
                        else:
                            print(f"❌ No valid previous state found with max_ones={min_ones}.")
                    else: # Global solve
                        init = self.solve_global_backwards(target, max_ones=500)
                        if init is not None:
                            self.game.grid = init
                            self.draw_grid(); pygame.display.flip()
                        else:
                            print("❌ No valid previous state found.")
                            
                elif event.key == pygame.K_ESCAPE:
                    self.selection_active = False
                    self.selection_start = self.selection_end = None

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if self.button_rect.collidepoint(mouse_pos):
                    self.open_initial_editor()
                    return
                
                if self.load_button_rect.collidepoint(mouse_pos):
                    if self.initial_declared_state is not None:
                        self.game.grid = self.initial_declared_state.copy()
                        self.back_steps = 0
                        print("✅ Loaded declared initial state into main grid.")
                    else:
                        print("⚠️ No initial state declared yet.")
                    return

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                # Start right-click selection
                self.selection_start = self.snap_to_grid(pygame.mouse.get_pos())
                self.selection_end = self.selection_start
                self.selection_active = True

            elif event.type == pygame.MOUSEMOTION and event.buttons[2]:
                self.selection_end = self.snap_to_grid(pygame.mouse.get_pos())

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self.selection_end = self.snap_to_grid(pygame.mouse.get_pos())
            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if self.button_rect.collidepoint(mouse_pos):
                    self.initial_declared_state = self.game.grid.copy()
                    self.back_steps = 0
                    self.button_color = (150, 255, 150)
                    print("✅ Declared current grid as initial state.")
                    return

            
    def solve_selection_backwards(self, target, buffer=10, max_attempts=3, max_ones=500):
        """
        Perform a backward solve on the current selection.
        After each local solve, check if the global grid evolves to the declared
        initial after `back_steps + 1` steps.
        """
        if not (self.selection_active and self.selection_start and self.selection_end):
            print("⚠️ No selection active.")
            return None
        if self.initial_declared_state is None:
            print("⚠️ No declared initial state.")
            return None

        # --- Selection bounds ---
        x0 = min(self.selection_start[0], self.selection_end[0]) // CELL_SIZE
        y0 = min(self.selection_start[1], self.selection_end[1]) // CELL_SIZE
        x1 = max(self.selection_start[0], self.selection_end[0]) // CELL_SIZE
        y1 = max(self.selection_start[1], self.selection_end[1]) // CELL_SIZE
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.game.width - 1, x1), min(self.game.height - 1, y1)

        sub_target = target[y0:y1+1, x0:x1+1]
        if np.count_nonzero(sub_target) == 0:
            print("⚠️ No live cells in selection — skipping.")
            return False

        gx0, gy0 = max(0, x0 - buffer), max(0, y0 - buffer)
        gx1, gy1 = min(self.game.width - 1, x1 + buffer), min(self.game.height - 1, y1 + buffer)

        exclude_models = []
        clean_solution = None

        for attempt in range(1, max_attempts + 1):
            print(f"🧩 Attempt {attempt}: solving backward for selection...")

            sub_init = solve_backward_components(
                sub_target,
                steps=1,
                buffer=buffer,
                timeout_ms=5000,
                exclude_models=exclude_models
            )

            if sub_init is None or not np.any(sub_init):
                print("❌ No solution found on this attempt.")
                continue

            # Record model for exclusion
            model_coords = [(y, x) for y in range(sub_init.shape[0])
                                    for x in range(sub_init.shape[1])
                                    if sub_init[y, x] == 1]
            exclude_models.append(model_coords)

            # Apply to a copy of the full grid
            test_game = GameOfLife(self.game.width, self.game.height, randomize=False)
            test_game.grid = self.game.grid.copy()
            test_game.grid[y0:y1+1, x0:x1+1] = sub_init

            # Step forward back_steps + 1 times
            # Step forward once and check directly against the current initial_declared_state
            test_game.step()
            

            
            consistent = np.array_equal(test_game.grid, self.initial_declared_state)
            fig, axes = plt.subplots(1, 2, figsize=(8, 4))
            axes[0].imshow(test_game.grid, cmap="gray_r")
            axes[0].set_title("Forward-evolved grid")
            axes[1].imshow(self.initial_declared_state, cmap="gray_r")
            axes[1].set_title("Declared initial")

            for ax in axes:
                ax.axis("off")

            plt.tight_layout()
            plt.show()
            if consistent:
                print("✅ Recursive consistency confirmed (whole grid matches initial).")
                clean_solution = sub_init
                self.initial_declared_state = self.game.grid.copy()
                self.initial_declared_state[y0:y1+1, x0:x1+1] = clean_solution
                self.game.grid[y0:y1+1, x0:x1+1] = clean_solution  # 🔥 Restore backward state
                self.back_steps += 1
                print(f"🌀 Declared full-grid new initial (depth {self.back_steps})")
                break
            else:
                print("❌ Inconsistent with current initial — retrying another model...")

        # If found, merge back into main grid
        if clean_solution is not None:
            self.game.grid[y0:y1+1, x0:x1+1] = clean_solution
            self.initial_declared_state = self.game.grid.copy()
            self.initial_chain.append(self.initial_declared_state.copy())
            self.draw_grid()
            pygame.display.flip()
            print("🧱 Local region updated and accepted.")
            return clean_solution

        print("❌ No consistent local solution found.")
        return None

    def solve_global_backwards(self, target, max_ones=500):
        print("🔍 Solving for previous step (global)...")
        min_ones = 1
        # max_ones is already set by the parameter for the initial broad search
        successful_init = None

        while min_ones < max_ones:
            mid_ones = (min_ones + max_ones) // 2
            current_init = solve_initial_for_target(
                target,
                steps=1,
                timeout_ms=5000,
                max_ones=mid_ones,
                restrict=True, # enforce that initial state is within some bounds
            )
            if current_init is not None:
                max_ones = mid_ones
                successful_init = current_init
                print(f"✅ Found a valid previous state with max_ones={mid_ones}.")
            else:
                min_ones = mid_ones + 1

        # After bisection, try one last time with min_ones to get the actual solution
        final_init = None
        if successful_init is not None: # Only proceed if some solution was found during bisection
            final_init = solve_initial_for_target(
                target,
                steps=1,
                timeout_ms=5000,
                max_ones=min_ones,
                restrict=True,
            )

        if final_init is not None:
            print(f"✅ Found a valid previous state with optimal max_ones={min_ones}!")
            return final_init
        else:
            print("❌ No valid previous state found.")
            return None


    def run(self):
        """Main simulation loop."""
        while self.running:
            self.handle_events()

            if not self.paused:
                # auto-run mode (space toggles this)
                self.game.step()
            elif self.step_once:
                # perform one step and pause again
                self.game.step()
                self.step_once = False

            self.draw_grid()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    GameOfLifeVisualizer().run()
