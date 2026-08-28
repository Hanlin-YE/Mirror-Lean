"""Top-level error detection algorithm.

Usage:
    from error_detection.detector import ErrorDetector
    from error_detection.loader import load_canonical_motion

    reference = load_canonical_motion("demo_output/reference_motion.json", source="robot")
    human = load_canonical_motion("demo_output/human_motion.json", source="human")

    detector = ErrorDetector()
    result = detector.detect(human, reference)
    print(result.primary_error.feature, result.primary_error.max_abs_error)
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from error_detection.alignment import DTWAligner
from error_detection.difference import DifferenceEngine
from error_detection.models import (
    CanonicalMotion,
    DetectionResult,
    ErrorScore,
)
from error_detection.ranker import ErrorRanker


class ErrorDetector:
    """Compare a human motion attempt against a robot reference and detect errors."""

    def __init__(
        self,
        feature_weights: Optional[Dict[str, float]] = None,
        max_error_threshold: float = 180.0,
    ):
        self.aligner = DTWAligner(feature_weights=feature_weights)
        self.difference_engine = DifferenceEngine()
        self.ranker = ErrorRanker(max_error_threshold=max_error_threshold)

    def _timing_error(
        self,
        reference_motion: CanonicalMotion,
        human_motion: CanonicalMotion,
        alignment: List[tuple[int, int]],
    ) -> float:
        """Mean absolute timestamp lag between aligned reference and human frames."""
        if not alignment or not reference_motion.poses or not human_motion.poses:
            return 0.0
        ref_ts = reference_motion.timestamps()
        hum_ts = human_motion.timestamps()
        diffs = [abs(ref_ts[i] - hum_ts[j]) for i, j in alignment]
        return float(np.mean(diffs))

    def detect(
        self,
        human_motion: CanonicalMotion,
        reference_motion: CanonicalMotion,
    ) -> DetectionResult:
        """Run the full detect pipeline: align, diff, rank."""
        alignment, _ = self.aligner.align(reference_motion, human_motion)

        differences = self.difference_engine.compute_sequence(
            reference_motion.poses,
            human_motion.poses,
            alignment,
        )

        ranked_errors = self.ranker.rank(differences)
        if not ranked_errors:
            raise ValueError("No errors detected; input motions may be empty.")

        timing_error = self._timing_error(reference_motion, human_motion, alignment)

        return DetectionResult(
            primary_error=ranked_errors[0],
            ranked_errors=ranked_errors,
            alignment=alignment,
            per_frame_differences=differences,
            reference_motion=reference_motion,
            human_motion=human_motion,
            timing_error=timing_error,
        )

    def compare_pair(
        self,
        human_path: str,
        reference_path: str,
    ) -> DetectionResult:
        """Convenience helper that loads two JSON files and runs detection."""
        from error_detection.loader import load_canonical_motion

        human = load_canonical_motion(human_path, source="human")
        reference = load_canonical_motion(reference_path, source="robot")
        return self.detect(human, reference)
