"""Compute interpretable feature differences between aligned human and robot poses."""

from __future__ import annotations

from typing import List

from error_detection.models import (
    AlignedDifference,
    CanonicalPose,
    CIRCULAR_FEATURES,
    FEATURES,
    FeatureDelta,
)


def angular_error(human_value: float, ref_value: float, circular: bool = False) -> float:
    """Compute signed error, using shortest-path wrap-around for circular features.

    Examples:
      angular_error(1.0, 359.0, circular=True) -> 2.0
      angular_error(10.0, 350.0, circular=True) -> 20.0
    """
    error = human_value - ref_value
    if not circular:
        return error
    # Wrap to [-180, 180)
    error = ((error + 180.0) % 360.0) - 180.0
    return error


class DifferenceEngine:
    """Compare canonical poses feature by feature after temporal alignment."""

    def __init__(self, feature_names: List[str] | None = None):
        self.feature_names = feature_names or FEATURES

    def compute(
        self,
        ref_pose: CanonicalPose,
        human_pose: CanonicalPose,
    ) -> AlignedDifference:
        """Return per-feature deltas for a single aligned pose pair."""
        deltas = []
        for feat in self.feature_names:
            r = getattr(ref_pose, feat)
            h = getattr(human_pose, feat)
            error = angular_error(h, r, circular=feat in CIRCULAR_FEATURES)
            deltas.append(
                FeatureDelta(
                    feature=feat,
                    ref_value=r,
                    human_value=h,
                    error=error,
                    abs_error=abs(error),
                    ref_timestamp=ref_pose.timestamp,
                    human_timestamp=human_pose.timestamp,
                )
            )
        return AlignedDifference(
            ref_pose=ref_pose,
            human_pose=human_pose,
            deltas=deltas,
        )

    def compute_sequence(
        self,
        ref_motion: List[CanonicalPose],
        human_motion: List[CanonicalPose],
        alignment: List[tuple[int, int]],
    ) -> List[AlignedDifference]:
        """Compute differences for every aligned frame pair."""
        return [
            self.compute(ref_motion[i], human_motion[j]) for i, j in alignment
        ]
