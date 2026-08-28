"""Temporal alignment between human and robot canonical motion sequences."""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
from error_detection.models import CanonicalMotion, CIRCULAR_FEATURES, FEATURES, FEATURE_RANGES


class DTWAligner:
    """Align two canonical motion sequences using Dynamic Time Warping."""

    def __init__(
        self,
        feature_weights: Dict[str, float] | None = None,
        normalize: bool = True,
        feature_ranges: Dict[str, float] | None = None,
    ):
        self.feature_weights = feature_weights or {}
        self.normalize = normalize
        self.feature_ranges = feature_ranges or {}

    def _to_matrix(self, motion: CanonicalMotion) -> np.ndarray:
        """Return raw feature matrix (N x F)."""
        return motion.to_array()

    def _feature_difference(self, x: float, y: float, feature: str) -> float:
        """Signed difference between two feature values; handles circular wrap."""
        if feature in CIRCULAR_FEATURES:
            return ((y - x + 180.0) % 360.0) - 180.0
        return y - x

    def _cost_matrix(
        self,
        X: np.ndarray,
        Y: np.ndarray,
    ) -> np.ndarray:
        """Compute pair-wise distance using circular-aware feature differences."""
        from error_detection.models import FEATURE_RANGES

        ranges = np.array(
            [self.feature_ranges.get(f, FEATURE_RANGES.get(f, 180.0)) for f in FEATURES],
            dtype=float,
        )
        ranges = np.where(ranges > 0, ranges, 1.0)
        weights = np.array(
            [self.feature_weights.get(f, 1.0) for f in FEATURES],
            dtype=float,
        )

        n, m = X.shape[0], Y.shape[0]
        cost = np.zeros((n, m), dtype=float)
        for i in range(n):
            for j in range(m):
                squared = 0.0
                for k, feat in enumerate(FEATURES):
                    diff = self._feature_difference(X[i, k], Y[j, k], feat)
                    if self.normalize:
                        diff = diff / ranges[k]
                    diff = diff * weights[k]
                    squared += diff * diff
                cost[i, j] = np.sqrt(squared)
        return cost

    def align(
        self,
        reference: CanonicalMotion,
        query: CanonicalMotion,
    ) -> Tuple[List[Tuple[int, int]], float]:
        """Return aligned index pairs (ref_idx, query_idx) and total DTW cost."""
        if not reference.poses or not query.poses:
            return [], float("inf")

        X = self._to_matrix(reference)
        Y = self._to_matrix(query)
        cost = self._cost_matrix(X, Y)

        n, m = cost.shape
        acc = np.zeros((n + 1, m + 1), dtype=float)
        acc[0, 1:] = np.inf
        acc[1:, 0] = np.inf

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                acc[i, j] = cost[i - 1, j - 1] + min(
                    acc[i - 1, j],
                    acc[i, j - 1],
                    acc[i - 1, j - 1],
                )

        # Backtrack from (n, m) to (1, 1)
        i, j = n, m
        path: List[Tuple[int, int]] = []
        while i > 0 and j > 0:
            path.append((i - 1, j - 1))
            diag = acc[i - 1, j - 1]
            left = acc[i, j - 1]
            up = acc[i - 1, j]
            if diag <= left and diag <= up:
                i -= 1
                j -= 1
            elif left < up:
                j -= 1
            else:
                i -= 1

        path.reverse()
        return path, float(acc[n, m])
