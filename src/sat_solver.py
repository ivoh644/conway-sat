import numpy as np
import random
from z3 import Solver, Bool, Sum, If, And, Or, Not, is_true, sat
from termcolor import colored
import threading

_z3_lock = threading.Lock()

def make_bool_grid(prefix, h, w, ctx=None):
    return [[Bool(f"{prefix}_{y}_{x}", ctx=ctx) for x in range(w)] for y in range(h)]


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

def life_transition(s, curr, nxt, neigh, ctx=None):
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
    timeout_ms=1000,
    restrict=True,
    max_ones=500,
    exclude_grids=None
):
    ctx = threading.local()
    if not hasattr(ctx, 'z3_ctx'):
        import z3
        ctx.z3_ctx = z3.Context()
    
    c = ctx.z3_ctx
    
    # We need to re-import Z3 helpers to use them with the specific context
    # but actually we can just pass the context to the constructors.
    
    margin = steps
    target = np.array(target, dtype=int)
    h, w = target.shape

    layers = [make_bool_grid(f"t{t}", h, w, ctx=c) for t in range(steps + 1)]

    s = Solver(ctx=c)
    if timeout_ms:
        s.set("timeout", timeout_ms)
    s.set("random_seed", random.randint(0, 10000)) # for new boards

    neigh = precompute_neighbors(h, w)
    
    for t in range(steps):
        life_transition(s, layers[t], layers[t + 1], neigh, ctx=c)

    # fix final state
    for y in range(h):
        for x in range(w):
            s.add(layers[steps][y][x] == bool(target[y, x]))

    # limit initial population
    s.add(
        Sum([layers[0][y][x] for y in range(h) for x in range(w)]) <= max_ones
    )

    if restrict:
        allowed = allowed_cells_from_target(target, steps, h, w)

        for y in range(h):
            for x in range(w):
                if (y, x) not in allowed:
                    s.add(layers[0][y][x] == False)

        s.add(Or([layers[0][y][x] for (y, x) in allowed]))

    if exclude_grids:
        for ex_grid in exclude_grids:
            max_true = int(ex_grid.sum())
            if max_true == 0:
                continue  # Skip empty grids

            # Create a list of conditions for each cell
            mismatch_conditions = []
            for y in range(h):
                for x in range(w):
                    ex_cell = bool(ex_grid[y, x])
                    mismatch_conditions.append(layers[0][y][x] != ex_cell)

            # Ensure less than 90% match of true values
            min_mismatches = int(max_true * 0.1) + 1
            s.add(Sum([If(cond, 1, 0) for cond in mismatch_conditions]) >= min_mismatches)
    
    print("  " + colored("Solving", "blue") + "...")

    if s.check() != sat:
        print("    " + colored("UNSAT", "red", attrs=["bold"]))
        return None

    print("    " + colored("SAT", "green") + " - extracting model")

    m = s.model()
    init = np.zeros((h, w), dtype=int)

    for y in range(h):
        for x in range(w):
            v = m.evaluate(layers[0][y][x], model_completion=True)
            init[y, x] = 1 if is_true(v) else 0

    return init



def solve_initial_minimal_iterative(
    target,
    steps=1,
    start_bound=2500,
    timeout_ms=5000,
    exclude_grids=None
):
    target = np.array(target, dtype=int)
    best = None
    bound = start_bound

    print(colored("Starting", "blue") + " iterative minimization")

    while bound >= 0:
        print("  " + colored("trying", "blue") + f" max_ones <= {bound}")

        sol = solve_initial_for_target(
            target,
            steps=steps,
            max_ones=bound,
            timeout_ms=timeout_ms,
            restrict=True,
            exclude_grids=exclude_grids
        )

        if sol is None:
            print("    " + colored("UNSAT", "red") + " at this bound")
            break
            
        best = sol
        ones = int(sol.sum())
        # THIS IS WACKY
        bound = ones - random.randint(1, 3)
        print("    " + colored("found", "green") + f" solution with {ones} live cells")

    if best is not None:
        print("  " + colored("Optimal", "green", attrs=["bold"]) + f" solution has {int(best.sum())} live cells")
    else:
        print(colored("No", "red", attrs=["bold"]) + " solution found at any bound")

    return best
