import numpy as np
from z3 import Solver, Bool, Sum, If, And, Or, Not, is_true, sat


# ---------- Game of Life transition ----------

def make_bool_grid(prefix, h, w):
    return [[Bool(f"{prefix}_{y}_{x}") for x in range(w)] for y in range(h)]


def neighbors(grid, x, y, h, w):
    ns = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                ns.append(grid[ny][nx])
    return ns

def precompute_neighbors(h, w):
    neigh = {}
    for y in range(h):
        for x in range(w):
            ns = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        ns.append((ny, nx))
            neigh[(y, x)] = ns
    return neigh

# def life_transition(s, curr, nxt, h, w):
#     for y in range(h):
#         for x in range(w):
#             n = neighbors(curr, x, y, h, w)
#             live = Sum([If(c, 1, 0) for c in n])
#             s.add(
#                 nxt[y][x]
#                 == Or(
#                     And(curr[y][x], Or(live == 2, live == 3)),
#                     And(Not(curr[y][x]), live == 3),
#                 )
#             )

def life_transition(s, curr, nxt, neigh):
    for (y, x), ns in neigh.items():
        live = Sum([If(curr[ny][nx], 1, 0) for ny, nx in ns])
        s.add(
            nxt[y][x]
            == Or(
                And(curr[y][x], Or(live == 2, live == 3)),
                And(Not(curr[y][x]), live == 3),
            )
        )

def allowed_cells_from_target(target, steps, h, w):
    ys, xs = np.where(target == 1)
    allowed = set()

    for ty, tx in zip(ys, xs):
        for dy in range(-steps, steps + 1):
            for dx in range(-steps, steps + 1):
                y = ty + dy
                x = tx + dx
                if 0 <= y < h and 0 <= x < w:
                    allowed.add((y, x))

    return allowed
# ---------- Backward SAT solver ----------


def solve_initial_for_target(
    target,
    steps=1,
    timeout_ms=10000,
    restrict=True,
    max_ones=500,
    exclude_grids=None
):
    """
    IMPORTANT SEMANTICS (matches your old working version):
    - Full grid is always used for ALL time steps
    - Bounding box restriction applies ONLY to t=0
    - Later layers are free to expand outside the window
    """
    margin = steps
    target = np.array(target, dtype=int)
    h, w = target.shape

    print("🧩 Building SAT instance")
    print(f"   grid = {w}×{h}, steps = {steps}")

    layers = [make_bool_grid(f"t{t}", h, w) for t in range(steps + 1)]

    s = Solver()
    if timeout_ms:
        s.set("timeout", timeout_ms)

    # transitions
    neigh = precompute_neighbors(h, w)
    
    for t in range(steps):
        life_transition(s, layers[t], layers[t + 1], neigh)

    # fix final state
    for y in range(h):
        for x in range(w):
            s.add(layers[steps][y][x] == bool(target[y, x]))

    # limit initial population
    s.add(
        Sum([layers[0][y][x] for y in range(h) for x in range(w)]) <= max_ones
    )

    # restrict INITIAL layer only (this is the critical bit)
    if restrict:
        allowed = allowed_cells_from_target(target, steps, h, w)

        print(f"   ↳ restricting t=0 to {len(allowed)} possible ancestor cells")

        for y in range(h):
            for x in range(w):
                if (y, x) not in allowed:
                    s.add(layers[0][y][x] == False)

        # require at least one live cell in allowed region
        s.add(Or([layers[0][y][x] for (y, x) in allowed]))
        
        
        # ys, xs = np.where(target == 1)
        # if len(xs) > 0:
        #     y_min = max(0, ys.min() - margin)
        #     y_max = min(h - 1, ys.max() + margin)
        #     x_min = max(0, xs.min() - margin)
        #     x_max = min(w - 1, xs.max() + margin)

        #     print(
        #         f"   ↳ restricting t=0 to window x=[{x_min},{x_max}], "
        #         f"y=[{y_min},{y_max}]"
        #     )

        #     for yy in range(h):
        #         for xx in range(w):
        #             if not (x_min <= xx <= x_max and y_min <= yy <= y_max):
        #                 s.add(layers[0][yy][xx] == False)

        #     # require at least one live cell inside window
        #     s.add(
        #         Or(
        #             [
        #                 layers[0][yy][xx]
        #                 for yy in range(y_min, y_max + 1)
        #                 for xx in range(x_min, x_max + 1)
        #             ]
        #         )
        #     )

    # Exclude specific grids from being returned as solutions for the initial layer
    if exclude_grids:
        for ex_grid in exclude_grids:
            clause = []
            for y in range(h):
                for x in range(w):
                    if ex_grid[y, x]:
                        clause.append(Not(layers[0][y][x]))
                    else:
                        clause.append(layers[0][y][x])
            s.add(Or(clause))

    print("🔍 Solving...")

    if s.check() != sat:
        print("❌ UNSAT")
        return None

    print("✅ SAT — extracting model")

    m = s.model()
    init = np.zeros((h, w), dtype=int)

    for y in range(h):
        for x in range(w):
            v = m.evaluate(layers[0][y][x], model_completion=True)
            init[y, x] = 1 if is_true(v) else 0

    print(f"🎯 Initial live cells: {int(init.sum())}")
    return init



def solve_initial_minimal_iterative(
    target,
    steps=1,
    start_bound=600,
    timeout_ms=5000,
    exclude_grids=None
):
    target = np.array(target, dtype=int)
    best = None
    bound = start_bound

    print("🔁 Starting iterative minimization")

    while bound >= 0:
        print(f"   trying max_ones ≤ {bound}")

        sol = solve_initial_for_target(
            target,
            steps=steps,
            max_ones=bound,
            timeout_ms=timeout_ms,
            restrict=True,
            exclude_grids=exclude_grids
        )

        if sol is None:
            print("   ↳ UNSAT at this bound")
            break

        best = sol
        ones = int(sol.sum())
        bound = ones - 1
        print(f"   ✓ found solution with {ones} live cells")

    if best is not None:
        print(f"🏁 Optimal solution has {int(best.sum())} live cells")
    else:
        print("🚫 No solution found at any bound")

    return best
