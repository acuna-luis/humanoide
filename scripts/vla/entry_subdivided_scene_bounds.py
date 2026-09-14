"""Finite-box partition for offline scene separation; never relaxes a bound."""
import time
import numpy as np


def partition_bound(query, center, widths, weights, *, threshold=.002000001,
                    max_nodes=512, seconds=5.):
    center, widths, weights = (np.asarray(v, float) for v in (center, widths, weights))
    if (center.ndim != 1 or widths.shape != center.shape or weights.shape != center.shape
            or not np.isfinite([center, widths, weights]).all()
            or (widths < 0).any() or (weights < 0).any()
            or max_nodes < 1 or not np.isfinite(seconds) or seconds <= 0):
        raise ValueError('Invalid partition parameters')
    pending = [(center, widths)]
    lower, nodes = float('inf'), 0
    deadline = time.monotonic()+seconds
    while pending:
        if nodes >= max_nodes or time.monotonic() >= deadline:
            return 0., nodes, False
        q, h = pending.pop()
        bound = float(query(q, h)); nodes += 1
        if not np.isfinite(bound) or bound < 0: raise ValueError('Invalid child bound')
        if bound > threshold:
            lower = min(lower, bound)
            continue
        axis = int(np.argmax(h*weights))
        if h[axis]*weights[axis] <= 1e-14: return 0., nodes, False
        half = h.copy(); half[axis] *= .5
        left, right = q.copy(), q.copy()
        left[axis] -= half[axis]; right[axis] += half[axis]
        pending.extend(((right, half.copy()), (left, half)))
    return lower, nodes, True


class SubdividedSceneBounds:
    def __init__(self, base, max_nodes):
        self.base, self.max_nodes = base, max_nodes
        self.partition_queries = 0
        self.partition_proofs = 0
        self.partition_incomplete = 0

    def __getattr__(self, name): return getattr(self.base, name)

    def interval_separations(self, q, half_widths, indices):
        result = self.base.interval_separations(q, half_widths, indices)
        # Only small error/trajectory boxes: large time intervals are subdivided
        # by the route certifier. This threshold changes computation, not error.
        if np.max(half_widths) > .020: return result
        for k, i in enumerate(indices):
            if result[k] > .002000001 or self.pairs[i][1] < self.robot_count: continue
            bound, nodes, complete = partition_bound(
                lambda center, widths: self.base.interval_separations(center, widths, [i])[0],
                q, half_widths, self.weights[i], max_nodes=self.max_nodes)
            self.partition_queries += nodes
            self.partition_proofs += int(complete)
            self.partition_incomplete += int(not complete)
            result[k] = max(result[k], bound)
        return result
