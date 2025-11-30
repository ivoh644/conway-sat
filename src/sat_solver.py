import numpy as np
from z3 import *
import itertools
try:
    from scipy.ndimage import label
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

# ---------- helpers ----------
def _find_components(target):
    """Return labeled array and number of components (8-connectivity)."""
    target = (np.array(target, dtype=int) > 0).astype(np.uint8)
    if _HAS_SCIPY:
        structure = np.ones((3,3), dtype=np.uint8)  # 8-connected
        labeled, n = label(target, structure=structure)
        return labeled, n
    # Fallback: simple BFS (slower, but OK for small grids)
    h, w = target.shape
    labeled = np.zeros_like(target, dtype=int)
    n = 0
    for y in range(h):
        for x in range(w):
            if target[y,x] and labeled[y,x] == 0:
                n += 1
                # BFS
                q = [(y,x)]
                labeled[y,x] = n
                while q:
                    cy,cx = q.pop()
                    for dy, dx in itertools.product((-1, 0, 1), repeat=2):
                        if dy==0 and dx==0: continue
                        ny,nx = cy+dy, cx+dx
                        if 0 <= ny < h and 0 <= nx < w and target[ny,nx] and labeled[ny,nx]==0:
                            labeled[ny,nx] = n
                            q.append((ny,nx))
    return labeled, n

def _boxes_from_labels(labeled, n_components, buffer, h, w):
    boxes = []
    for i in range(1, n_components+1):
        ys, xs = np.where(labeled == i)
        if len(xs) == 0:
            continue
        y0, y1 = ys.min()-buffer, ys.max()+buffer
        x0, x1 = xs.min()-buffer, xs.max()+buffer
        # clamp
        y0 = max(0, y0); y1 = min(h-1, y1)
        x0 = max(0, x0); x1 = min(w-1, x1)
        boxes.append([y0, y1, x0, x1])
    return boxes

def _overlap(a, b):
    ay0, ay1, ax0, ax1 = a
    by0, by1, bx0, bx1 = b
    return ax1 >= bx0 and bx1 >= ax0 and ay1 >= by0 and by1 >= ay0

def _merge_two(a, b):
    ay0, ay1, ax0, ax1 = a
    by0, by1, bx0, bx1 = b
    return [min(ay0,by0), max(ay1,by1), min(ax0,bx0), max(ax1,bx1)]

def _merge_overlapping_boxes(boxes):
    # O(n^2) merge until stable; n is small (components)
    boxes = boxes[:]
    changed = True
    while changed:
        changed = False
        out = []
        used = [False]*len(boxes)
        for i in range(len(boxes)):
            if used[i]: continue
            cur = boxes[i]
            for j in range(i+1, len(boxes)):
                if used[j]: continue
                if _overlap(cur, boxes[j]):
                    cur = _merge_two(cur, boxes[j])
                    used[j] = True
                    changed = True
            used[i] = True
            out.append(cur)
        boxes = out
    return boxes

# ---------- existing solver (single window) ----------
def make_bool_grid(prefix, width, height):
    return [[Bool(f"{prefix}_{y}_{x}") for x in range(width)] for y in range(height)]

def neighbor_bools(grid, x, y, width, height, wrap=False):
    ns=[]
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dx==0 and dy==0: continue
            nx, ny = x+dx, y+dy
            if wrap:
                nx %= width; ny %= height
                ns.append(grid[ny][nx])
            elif 0 <= nx < width and 0 <= ny < height:
                ns.append(grid[ny][nx])
    return ns

def life_transition(s, curr, nxt, width, height, wrap=False):
    for y in range(height):
        for x in range(width):
            cell = curr[y][x]
            neighbors = neighbor_bools(curr, x, y, width, height, wrap)
            live_count = Sum([If(n,1,0) for n in neighbors])
            survive = And(cell, Or(live_count==2, live_count==3))
            born    = And(Not(cell), live_count==3)
            s.add(nxt[y][x] == Or(survive, born))

from z3 import is_true
def solve_initial_for_target(
    target,
    steps=1,
    wrap=False,
    timeout_ms=10000,
    margin=3,
    restrict=True,
    exclude_models=None,
    max_ones=500
):
    target = np.array(target, dtype=int)
    h, w = target.shape
    layers = [make_bool_grid(f"t{t}", w, h) for t in range(steps+1)]
    #add constraint that the number of ones is less than max_ones
    
    s = Solver()
    if timeout_ms: s.set("timeout", timeout_ms)
    for t in range(steps):
        life_transition(s, layers[t], layers[t+1], w, h, wrap=wrap)

    for y in range(h):
        for x in range(w):
            s.add(layers[steps][y][x] == bool(target[y,x]))
    s.add(Sum([layers[0][y][x] for y in range(h) for x in range(w)]) <= max_ones)
    if restrict:
        ys, xs = np.where(target==1)
        if len(xs) > 0:
            y_min, y_max = max(0, ys.min()-margin), min(h-1, ys.max()+margin)
            x_min, x_max = max(0, xs.min()-margin), min(w-1, xs.max()+margin)
            print(f"   ↳ window x=[{x_min},{x_max}], y=[{y_min},{y_max}]")
            # force outside window to be dead
            for yy in range(h):
                for xx in range(w):
                    if not (x_min <= xx <= x_max and y_min <= yy <= y_max):
                        s.add(layers[0][yy][xx] == False)
            # also require at least one cell alive inside window
            s.add(Or([layers[0][yy][xx] for yy in range(y_min, y_max+1) for xx in range(x_min, x_max+1)]))

    # --- Exclude previously found models (diversity) ---
    if exclude_models:
        for prev_model in exclude_models:
            diff_clause = [Not(layers[0][y][x]) for (y, x) in prev_model
                           if 0 <= y < len(layers[0]) and 0 <= x < len(layers[0][0])]
            if diff_clause:
                s.add(Or(diff_clause))
            
    if s.check() != sat:
        return None

    m = s.model()
    init = np.zeros((h,w), dtype=int)
    for y in range(h):
        for x in range(w):
            v = m.evaluate(layers[0][y][x], model_completion=True)
            init[y,x] = 1 if is_true(v) else 0
    return init

# ---------- component solver ----------
def bounding_boxes_from_components(target, buffer=3):
    target = (np.array(target, dtype=int) > 0).astype(np.uint8)
    h, w = target.shape
    labeled, n = _find_components(target)
    if n == 0:
        return []

    raw = _boxes_from_labels(labeled, n, buffer, h, w)
    merged = _merge_overlapping_boxes(raw)

    # Logging for clarity
    print(f"🧩 components: {n}, raw boxes: {raw}, merged: {merged}")
    return merged

def solve_backward_components(target, steps=1, buffer=3, timeout_ms=5000, wrap=False, exclude_models=None):
    target = np.array(target, dtype=int)
    h, w = target.shape
    boxes = bounding_boxes_from_components(target, buffer=buffer)
    if not boxes:
        print("⚠️ No live components; nothing to backsolve.")
        return np.zeros_like(target)

    combined = np.zeros_like(target)
    for i, (y0,y1,x0,x1) in enumerate(boxes, start=1):
        print(f"   🔹 Region {i}: x=[{x0},{x1}], y=[{y0},{y1}]")
        sub_tgt = target[y0:y1+1, x0:x1+1]
        sub_init = solve_initial_for_target(
            sub_tgt,
            steps=steps,
            wrap=wrap,
            timeout_ms=timeout_ms,
            margin=0,
            restrict=False,
            exclude_models=exclude_models
        )
        if sub_init is not None:
            combined[y0:y1+1, x0:x1+1] |= sub_init
    return combined
