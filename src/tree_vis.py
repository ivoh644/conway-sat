import pygame
import numpy as np
import os
import datetime
import threading
import time
from game_of_life import GameOfLife
import random
from sat_solver import solve_initial_for_target, solve_initial_minimal_iterative
from termcolor import colored
import pickle

CELL = 10
FPS = 30
TOP = 60
SIDEBAR_WIDTH = 400
GRID_COLOR = (200, 200, 200)
DEAD = (255, 255, 255)
ALIVE_COLOR = (40, 40, 40)
HIGHLIGHT_COLOR = (255, 100, 100)

VIRIDIS_COLORS = [
    (68, 1, 84), (71, 44, 122), (59, 81, 139), (44, 113, 142),
    (33, 144, 141), (39, 173, 129), (92, 200, 99), (170, 220, 50), (253, 231, 37)
]

def get_viridis_color(n_idx):
    # n_idx is number of neighbors (0-8)
    return VIRIDIS_COLORS[int(n_idx)]

class Node:
    def __init__(self, grid, parent=None):
        self.grid = grid.copy()
        self.parent = parent
        self.children = []
        self.excluded_from_sat = [] # List of grids already tried as ancestors
        self.x = 0
        self.y = 0
        self.rect = pygame.Rect(0, 0, 40, 30)

    @property
    def depth(self):
        d = 0
        curr = self
        while curr.parent:
            d += 1
            curr = curr.parent
        return d

    def add_child(self, grid):
        child = Node(grid, parent=self)
        self.children.append(child)
        return child

    def add_child_node(self, child_node):
        self.children.append(child_node)
        child_node.parent = self

class TreeVisualizer:
    def __init__(self, w=30, h=30):
        pygame.init()
        self.w, self.h = w, h
        self.game = GameOfLife(w, h, randomize=True)
        
        # Screen: Left is Grid, Right is Tree
        self.grid_width = w * CELL
        self.grid_height = h * CELL
        self.screen_h = self.grid_height + TOP
        self.screen_w = self.grid_width + SIDEBAR_WIDTH
        
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption("Tree Visualization - Game of Life")
        self.clock = pygame.time.Clock()
        self.paused = True
        
        # Threading & Search state
        self.searching = False
        self.lock = threading.Lock()
        self.search_thread = None
        
        self.loading = False

        self.font = pygame.font.SysFont("Arial", 12)
        self.depth_font = pygame.font.SysFont("Arial", 10, italic=True)
        self.btn_font = pygame.font.SysFont("Arial", 15, bold=True)
        
        # Scrolling & Zoom
        self.tree_offset_x = 0
        self.tree_offset_y = 0
        self.zoom_level = 1.0

        
        self.save_grid_btn = pygame.Rect(10, 15, 60, 30)
        self.load_grid_btn = pygame.Rect(80, 15, 60, 30)
        self.save_tree_btn = pygame.Rect(150, 15, 60, 30)
        self.load_tree_btn = pygame.Rect(220, 15, 60, 30)
        self.clear_btn = pygame.Rect(290, 15, 60, 30)
        self.step_btn = pygame.Rect(360, 15, 60, 30)
        self.go_deeper_btn = pygame.Rect(430, 15, 100, 30)

        self.roots = [Node(self.game.grid)]
        self.current_node = self.roots[0]
        self.config_files = []

    def neighbors(self, grid):
        return sum(
            np.roll(np.roll(grid, i, 0), j, 1)
            for i in (-1, 0, 1)
            for j in (-1, 0, 1)
            if (i, j) != (0, 0)
        )

    def draw_grid(self):
        with self.lock:
            grid_to_draw = self.game.grid.copy()
        
        screen_grid_rect = pygame.Rect(0, TOP, self.grid_width, self.grid_height)
        pygame.draw.rect(self.screen, DEAD, screen_grid_rect)
        
        neigh = self.neighbors(grid_to_draw)
        for y in range(self.h):
            for x in range(self.w):
                if grid_to_draw[y, x]:
                    color = get_viridis_color(neigh[y, x])
                    pygame.draw.rect(
                        self.screen,
                        color,
                        (x * CELL, y * CELL + TOP, CELL, CELL),
                    )

        for x in range(self.w + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (x * CELL, TOP), (x * CELL, TOP + self.grid_height))
        for y in range(self.h + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y * CELL + TOP), (self.grid_width, y * CELL + TOP))

    def draw_tree(self):
        tree_rect = pygame.Rect(self.grid_width, 0, SIDEBAR_WIDTH, self.screen_h)
        pygame.draw.rect(self.screen, (240, 240, 240), tree_rect)
        
        old_clip = self.screen.get_clip()
        self.screen.set_clip(tree_rect)

        # Scaled dimensions
        node_w = int(40 * self.zoom_level)
        node_h = int(30 * self.zoom_level)
        depth_spacing = int(60 * self.zoom_level)
        width_spacing = int(60 * self.zoom_level)

        with self.lock:
            def get_width(node):
                if not node.children:
                    return width_spacing
                return sum(get_width(c) for c in node.children)

            def layout(node, x, y):
                node.x = self.grid_width + (x + self.tree_offset_x) * self.zoom_level
                node.y = (y + self.tree_offset_y) * self.zoom_level
                

                node.rect.w = node_w
                node.rect.h = node_h
                node.rect.center = (node.x, node.y)
                
                if not node.children:
                    return
                
                total_w = get_width(node)
                curr_x = x - total_w // 2 / self.zoom_level
                
                def get_vwidth(node):
                    if not node.children: return 60
                    return sum(get_vwidth(c) for c in node.children)
                
                vw = get_vwidth(node)
                curr_vx = x - vw // 2
                for child in node.children:
                    cvw = get_vwidth(child)
                    layout(child, curr_vx + cvw // 2, y + 60)
                    curr_vx += cvw

            vx_base = SIDEBAR_WIDTH // 2 / self.zoom_level
            for i, root in enumerate(self.roots):
                layout(root, vx_base, 80 / self.zoom_level + i * 200)

            # Draw edges and nodes
            def draw_edges(node):
                for child in node.children:
                    pygame.draw.line(self.screen, (150, 150, 150), (node.x, node.y), (child.x, child.y), max(1, int(2 * self.zoom_level)))
                    draw_edges(child)
            
            def draw_nodes(node):
                for child in node.children:
                    draw_nodes(child)
                
                color = (100, 255, 100) if node == self.current_node else (220, 220, 220)
                pygame.draw.rect(self.screen, color, node.rect, border_radius=max(1, int(5 * self.zoom_level)))
                pygame.draw.rect(self.screen, (50, 50, 50), node.rect, max(1, int(1 * self.zoom_level)), border_radius=max(1, int(5 * self.zoom_level)))
                
                if self.zoom_level > 0.4:
                    label = self.font.render(f"{int(node.grid.sum())}", True, (0, 0, 0))
                    self.screen.blit(label, (node.rect.x + (node.rect.w - label.get_width())//2, node.rect.y + (node.rect.h - label.get_height())//2))
                    
                    depth_label = self.depth_font.render(f"d:{node.depth}", True, (100, 100, 100))
                    self.screen.blit(depth_label, (node.rect.right + 2, node.rect.y))

            for root in self.roots:
                draw_edges(root)
                draw_nodes(root)
        
        self.screen.set_clip(old_clip)
        pygame.draw.line(self.screen, (150, 150, 150), (self.grid_width, 0), (self.grid_width, self.screen_h), 2)

    def draw_ui(self):
        pygame.draw.rect(self.screen, (220, 220, 220), (0, 0, self.screen_w, TOP))
        
        with self.lock:
            searching = self.searching

        if searching:
            go_deeper_text = "Searching..."
            go_deeper_color = (100, 255, 100)
        else:
            go_deeper_text = "Go Deeper"
            go_deeper_color = (255, 255, 100)

        for btn, text, color in [
            (self.save_grid_btn, "Save G", (200, 255, 200)),
            (self.load_grid_btn, "Load G", (200, 220, 255)),
            (self.save_tree_btn, "Save T", (150, 255, 150)),
            (self.load_tree_btn, "Load T", (150, 200, 255)),
            (self.clear_btn, "Clear", (255, 200, 200)),
            (self.step_btn, "Step", (220, 220, 220)),
            (self.go_deeper_btn, go_deeper_text, go_deeper_color)
        ]:
            pygame.draw.rect(self.screen, color, btn, border_radius=5)
            pygame.draw.rect(self.screen, (0, 0, 0), btn, 1, border_radius=5)
            txt_surf = self.btn_font.render(text, True, (0, 0, 0))
            self.screen.blit(txt_surf, (btn.x + (btn.w - txt_surf.get_width())//2, btn.y + (btn.h - txt_surf.get_height())//2))

    def _scan_configs(self, extension=".npz"):
        path = os.path.join(os.path.dirname(__file__), "..", "data")
        if not os.path.isdir(path):
            return []
        return sorted(
            f for f in os.listdir(path)
            if f.endswith(extension)
        )

    def open_load_menu(self, mode="grid"):
        self.load_mode = mode # "grid" or "tree"
        ext = ".npz" if mode == "grid" else ".tree.pkl"
        self.config_files = self._scan_configs(ext)
        if not self.config_files:
            print(colored("WARNING:", "yellow", attrs=["bold"]) + f" No saved {mode} configs found.")
            return
        self.loading = True
        with self.lock:
            self.searching = False

    def draw_load_menu(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((240, 240, 240, 240))
        self.screen.blit(overlay, (0, 0))

        title = self.btn_font.render("Select configuration to load", True, (0, 0, 0))
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

    def search_worker(self):
        """Background thread for the SAT solver."""
        while True:
            with self.lock:
                if not self.searching:
                    break
                node = self.current_node
                
                if len(node.children) > 4:
                    print("  " + colored("Too", "red") + " many branches, backtracking...")
                    if node.parent:
                        self.current_node = node.parent
                        self.game.grid = self.current_node.grid.copy()
                        continue
                    else:
                        print("  " + colored("Already", "red") + " at root, stopping search.")
                        self.searching = False
                        break
                
                grid_copy = node.grid.copy()
                excluded_copy = [g.copy() for g in node.excluded_from_sat]
                current_depth = node.depth

            ancestor = solve_initial_minimal_iterative(
                grid_copy,
                steps=1,
                timeout_ms=10000 * max(1, current_depth),
                exclude_grids=excluded_copy
            )
            
            with self.lock:
                if not self.searching:
                    break
                
                if ancestor is not None:
                    print("  " + colored("Found", "green") + " ancestor")
                    new_node = self.current_node.add_child(ancestor)
                    self.current_node.excluded_from_sat.append(ancestor)
                    self.current_node = new_node
                    self.game.grid = new_node.grid.copy()
                else:
                    print("  " + colored("No", "red") + " more ancestors, backtracking...")
                    if random.random() < 0.15:
                        steps = random.randint(1, self.current_node.depth)
                        print("  " + colored("Backtracking", "red") + f" {steps} steps")
                        for _ in range(steps):
                            if self.current_node.parent:
                                self.current_node = self.current_node.parent
                                self.game.grid = self.current_node.grid.copy()
                            else:
                                break
                    else:
                        print("  " + colored("Backtracking", "red") + " 1 step")
                        if self.current_node.parent:
                            self.current_node = self.current_node.parent
                            self.game.grid = self.current_node.grid.copy()
                        else:
                            self.searching = False
                            break
            
            # Short sleep to prevent tight loop if SAT finishes instantly
            time.sleep(0.1)

    def toggle_search(self):
        with self.lock:
            self.searching = not self.searching
            if self.searching:
                if self.search_thread is None or not self.search_thread.is_alive():
                    self.search_thread = threading.Thread(target=self.search_worker, daemon=True)
                    self.search_thread.start()

    def step_forward(self):
        with self.lock:
            if self.current_node.parent:
                # If we are at an ancestor and step forward, move towards the future (root)
                self.current_node = self.current_node.parent
                self.game.grid = self.current_node.grid.copy()
            else:
                # If we are at the latest state (no parent), calculate new state
                self.game.step()
                new_node = Node(self.game.grid)
                new_node.add_child_node(self.current_node)
                self.current_node.parent = new_node
                
                # If the current node was a root, update the root list
                if self.current_node in self.roots:
                    idx = self.roots.index(self.current_node)
                    self.roots[idx] = new_node
                
                self.current_node = new_node

    def handle_events(self):
        keys = pygame.key.get_pressed()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            
            # --- LOADING MODE ---
            if self.loading:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.loading = False
                if e.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    idx = (my - 50) // 24
                    if 0 <= idx < len(self.config_files):
                        path = os.path.join(os.path.dirname(__file__), "..", "data", self.config_files[idx])
                        if self.load_mode == "grid":
                            data = np.load(path)
                            with self.lock:
                                self.game.grid = data["grid"].copy()
                                new_root = Node(self.game.grid)
                                self.roots.append(new_root) # Add as new disconnected root
                                self.current_node = new_root
                                self.searching = False
                        else:
                            with open(path, "rb") as f:
                                data = pickle.load(f)
                            with self.lock:
                                self.roots = data["roots"]
                                self.current_node = data["current_node"]
                                self.game.grid = self.current_node.grid.copy()
                                self.searching = False
                        self.loading = False
                        self.paused = True
                        print(colored("Loaded", "green") + f" {self.config_files[idx]}")
                continue

            # --- NORMAL MODE ---
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                if self.save_grid_btn.collidepoint(mx, my):
                    self.save_grid()
                elif self.load_grid_btn.collidepoint(mx, my):
                    self.open_load_menu(mode="grid")
                elif self.save_tree_btn.collidepoint(mx, my):
                    self.save_tree()
                elif self.load_tree_btn.collidepoint(mx, my):
                    self.open_load_menu(mode="tree")
                elif self.clear_btn.collidepoint(mx, my):
                    with self.lock:
                        self.game.grid[:] = 0
                        new_root = Node(self.game.grid)
                        self.roots = [new_root]
                        self.current_node = new_root
                        self.searching = False
                elif self.step_btn.collidepoint(mx, my):
                    self.step_forward()
                    with self.lock: self.searching = False
                elif self.go_deeper_btn.collidepoint(mx, my):
                    self.toggle_search()
                else:
                    with self.lock:
                        is_searching = self.searching
                    
                    if not is_searching:
                        def check_nodes(node):
                            if node.rect.collidepoint(mx, my):
                                with self.lock:
                                    self.current_node = node
                                    self.game.grid = node.grid.copy()
                                    self.searching = False 
                                return True
                            for child in node.children:
                                if check_nodes(child): return True
                            return False
                        
                        found = False
                        for root in self.roots:
                            if check_nodes(root):
                                found = True
                                break
                        
                        if not found:
                            # Grid interaction
                            gx, gy = mx // CELL, (my - TOP) // CELL
                            if 0 <= gx < self.w and 0 <= gy < self.h:
                                with self.lock:
                                    self.game.grid[gy, gx] ^= 1
                                    new_root = Node(self.game.grid)
                                    self.roots.append(new_root)
                                    self.current_node = new_root
                                    self.searching = False

            if e.type == pygame.MOUSEWHEEL:
                if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                    
                    old_zoom = self.zoom_level
                    self.zoom_level *= (1.1 ** e.y)
                    self.zoom_level = max(0.1, min(self.zoom_level, 5.0))
                elif keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    self.tree_offset_x += e.y * 30 / self.zoom_level
                else:
                    self.tree_offset_y += e.y * 30 / self.zoom_level

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    if not self.paused:
                        with self.lock: self.searching = False
                elif e.key == pygame.K_b:
                    self.toggle_search()
                elif e.key == pygame.K_s:
                    self.save_grid()
                elif e.key == pygame.K_c:
                    with self.lock:
                        self.game.grid[:] = 0
                        new_root = Node(self.game.grid)
                        self.roots = [new_root]
                        self.current_node = new_root
                        self.searching = False
                elif e.key == pygame.K_RIGHT:
                    self.step_forward()
                    with self.lock: self.searching = False
                elif e.key == pygame.K_HOME:
                    self.tree_offset_x = 0
                    self.tree_offset_y = 0
                    self.zoom_level = 1.0

        return True

    def save_grid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(path, exist_ok=True)
        name = datetime.datetime.now().strftime("grid_%Y%m%d_%H%M%S.npz")
        with self.lock:
            grid_to_save = self.game.grid.copy()
        np.savez_compressed(os.path.join(path, name), grid=grid_to_save)
        print(colored("Saved Grid", "green", attrs=["bold"]) + f" {name}")

    def save_tree(self):
        path = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(path, exist_ok=True)
        name = datetime.datetime.now().strftime("tree_%Y%m%d_%H%M%S.tree.pkl")
        with self.lock:
            # We save roots and current_node reference. 
            # Note: pickle might hit recursion depth for very large trees.
            data = {
                "roots": self.roots,
                "current_node": self.current_node,
                "w": self.w,
                "h": self.h
            }
        with open(os.path.join(path, name), "wb") as f:
            pickle.dump(data, f)
        print(colored("Saved Tree", "green", attrs=["bold"]) + f" {name}")

    def run(self):
        while True:
            if not self.handle_events():
                break
            
            with self.lock:
                is_searching = self.searching
                is_paused = self.paused
                is_loading = self.loading
            
            if not is_searching and not is_paused and not is_loading:
                self.step_forward()
            
            self.screen.fill((255, 255, 255))
            self.draw_grid()
            self.draw_tree()
            self.draw_ui()

            if self.loading:
                self.draw_load_menu()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    TreeVisualizer(w=80, h=80).run()
