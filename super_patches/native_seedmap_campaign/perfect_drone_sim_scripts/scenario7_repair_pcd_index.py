"""Exact legacy PCD queries without Python iteration over empty grid cells.

The frozen observer's grid, point order, float32 arithmetic, radius predicate,
and strict minimum comparisons are retained. Only enumeration of occupied grid
cells changes: vectorized index comparisons replace thousands of Python lookups
in empty space. No SciPy dependency, sampling, approximation, or skipped callback
is introduced.
"""
import numpy as np


INDEX_POLICY = "exact-vectorized-occupied-cell-enumeration-v1"


def optimized_index_class(legacy_class):
    class ExactOccupiedCellIndex(legacy_class):
        def __init__(self, path):
            super().__init__(path)
            # Legacy __init__ inserts lexicographically sorted cell keys. The
            # same order matches itertools.product's ordering in every cube
            # or shell, including equal-distance nearest-point tie breaks.
            self._cell_keys = np.asarray(list(self.cells), dtype=np.int32).reshape(-1, 3)
            self._cell_bounds = np.asarray(list(self.cells.values()), dtype=np.int64).reshape(-1, 2)

        def _points_in_cells(self, indices):
            if not len(indices):
                return np.empty((0, 3), dtype=np.float32)
            chunks = [self.points[start:end]
                      for start, end in self._cell_bounds[indices]]
            return np.concatenate(chunks)

        def nearby_points(self, position, radius_m=1.0):
            center = np.floor(position / self.CELL_M).astype(np.int32)
            reach = int(np.ceil(radius_m / self.CELL_M))
            selected = np.all((self._cell_keys >= center - reach)
                              & (self._cell_keys <= center + reach), axis=1)
            candidates = self._points_in_cells(np.flatnonzero(selected))
            if not len(candidates):
                return candidates
            delta = candidates - position
            return candidates[np.einsum("ij,ij->i", delta, delta) <= radius_m**2]

        def nearest(self, position, max_distance_m=None):
            if max_distance_m is not None:
                # Reuse the frozen radius predicate and reduction unchanged.
                return super().nearest(position, max_distance_m=max_distance_m)
            if not len(self._cell_keys):
                raise ValueError("Cannot query an empty static PCD index")
            center = np.floor(position / self.CELL_M).astype(np.int32)
            shell = np.max(np.abs(self._cell_keys - center), axis=1)
            best_distance_sq = float("inf")
            best_point = None
            for reach in np.unique(shell):
                candidates = self._points_in_cells(np.flatnonzero(shell == reach))
                delta = candidates - position
                distance_sq = np.einsum("ij,ij->i", delta, delta)
                index = int(np.argmin(distance_sq))
                if float(distance_sq[index]) < best_distance_sq:
                    best_distance_sq = float(distance_sq[index])
                    best_point = candidates[index]
                low = (center - reach) * self.CELL_M
                high = (center + reach + 1) * self.CELL_M
                unsearched_lower_bound = float(
                    np.min(np.concatenate((position - low, high - position))))
                if best_distance_sq <= unsearched_lower_bound**2:
                    return float(np.sqrt(best_distance_sq)), best_point
            # All nonempty cells have been visited; empty outer shells cannot
            # improve the result. Unlike a fixed search radius this is global.
            return float(np.sqrt(best_distance_sq)), best_point

    return ExactOccupiedCellIndex
