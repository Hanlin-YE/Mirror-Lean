"""Rank detected errors and select the primary one to demonstrate."""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from error_detection.models import (
    AlignedDifference,
    ErrorScore,
    FEATURES,
    FeatureDelta,
)


class ErrorRanker:
    """Select the single most important error for feedback / MIRROR / MORPH."""

    # Feature weights tuned so large visible errors matter most.
    FEATURE_IMPORTANCE: Dict[str, float] = {
        "left_arm_elevation": 1.0,
        "right_arm_elevation": 1.0,
        "left_arm_azimuth": 0.8,
        "right_arm_azimuth": 0.8,
        "left_elbow_flexion": 0.7,
        "right_elbow_flexion": 0.7,
        "torso_yaw": 0.5,
        "torso_lean": 0.5,
    }

    def __init__(self, max_error_threshold: float = 180.0):
        self.max_error_threshold = max_error_threshold

    def rank(self, differences: List[AlignedDifference]) -> List[ErrorScore]:
        """Aggregate errors per feature and return a ranked list."""
        per_feature: Dict[str, List[float]] = {f: [] for f in FEATURES}
        for diff in differences:
            for d in diff.deltas:
                per_feature[d.feature].append(d.error)

        scores = []
        for feat, errors in per_feature.items():
            if not errors:
                continue
            arr = np.array(errors)
            mean_err = float(np.mean(arr))
            std_err = float(np.std(arr))
            max_abs = float(np.max(np.abs(arr)))

            # Confidence: higher when the error is significant and consistent.
            significance = min(max_abs / self.max_error_threshold, 1.0)
            consistency = 1.0 - min(std_err / (self.max_error_threshold / 2.0), 1.0)
            confidence = significance * 0.6 + consistency * 0.4

            importance = self.FEATURE_IMPORTANCE.get(feat, 1.0)
            scores.append(
                ErrorScore(
                    feature=feat,
                    mean_error=mean_err,
                    std_error=std_err,
                    max_abs_error=max_abs,
                    confidence=round(confidence, 3),
                    feature_importance=importance,
                )
            )

        scores.sort(
            key=lambda s: s.max_abs_error * s.feature_importance * s.confidence,
            reverse=True,
        )
        return scores

    def primary_error(self, differences: List[AlignedDifference]) -> Optional[ErrorScore]:
        """Return the highest ranked error, or None if no errors exist."""
        ranked = self.rank(differences)
        return ranked[0] if ranked else None
