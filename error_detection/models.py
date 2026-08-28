"""Data models shared across the error detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np


FEATURES = [
    "left_arm_elevation",
    "right_arm_elevation",
    "left_arm_azimuth",
    "right_arm_azimuth",
    "left_elbow_flexion",
    "right_elbow_flexion",
    "torso_yaw",
    "torso_lean",
]

# Typical observed range for each canonical feature, used for normalization and
# confidence calibration. Values can be overridden by the aligner/ranker.
FEATURE_RANGES: Dict[str, float] = {
    "left_arm_elevation": 180.0,
    "right_arm_elevation": 180.0,
    "left_arm_azimuth": 360.0,
    "right_arm_azimuth": 360.0,
    "left_elbow_flexion": 180.0,
    "right_elbow_flexion": 180.0,
    "torso_yaw": 180.0,
    "torso_lean": 90.0,
}

# Features whose values wrap around (e.g. 359° is only 2° away from 1°).
CIRCULAR_FEATURES = {
    "left_arm_azimuth",
    "right_arm_azimuth",
    "torso_yaw",
}


@dataclass
class CanonicalPose:
    """A single frame in the shared canonical motion space."""

    timestamp: float = 0.0
    left_arm_elevation: float = 0.0
    right_arm_elevation: float = 0.0
    left_arm_azimuth: float = 0.0
    right_arm_azimuth: float = 0.0
    left_elbow_flexion: float = 0.0
    right_elbow_flexion: float = 0.0
    torso_yaw: float = 0.0
    torso_lean: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                self.left_arm_elevation,
                self.right_arm_elevation,
                self.left_arm_azimuth,
                self.right_arm_azimuth,
                self.left_elbow_flexion,
                self.right_elbow_flexion,
                self.torso_yaw,
                self.torso_lean,
            ],
            dtype=float,
        )

    @classmethod
    def from_array(cls, arr: np.ndarray, timestamp: float = 0.0) -> "CanonicalPose":
        return cls(timestamp=timestamp, **dict(zip(FEATURES, arr)))

    def to_dict(self) -> Dict[str, float]:
        return {"timestamp": self.timestamp, **{f: getattr(self, f) for f in FEATURES}}


@dataclass
class CanonicalMotion:
    """A time sequence of canonical poses."""

    poses: List[CanonicalPose] = field(default_factory=list)
    source: str = "unknown"

    def __len__(self) -> int:
        return len(self.poses)

    def to_array(self) -> np.ndarray:
        if not self.poses:
            return np.empty((0, len(FEATURES)))
        return np.stack([p.to_array() for p in self.poses])

    def timestamps(self) -> np.ndarray:
        return np.array([p.timestamp for p in self.poses])

    @classmethod
    def from_array(
        cls,
        arr: np.ndarray,
        timestamps: np.ndarray | None = None,
        source: str = "unknown",
    ) -> "CanonicalMotion":
        if timestamps is None:
            timestamps = np.arange(arr.shape[0]) / 30.0
        poses = [CanonicalPose.from_array(row, t) for row, t in zip(arr, timestamps)]
        return cls(poses=poses, source=source)


@dataclass
class FeatureDelta:
    """Difference for one feature at one aligned frame pair."""

    feature: str
    ref_value: float
    human_value: float
    error: float
    abs_error: float
    ref_timestamp: float
    human_timestamp: float


@dataclass
class AlignedDifference:
    """All per-feature differences for one aligned frame pair."""

    ref_pose: CanonicalPose
    human_pose: CanonicalPose
    deltas: List[FeatureDelta]


@dataclass
class ErrorScore:
    """Aggregated error for one feature across the whole sequence."""

    feature: str
    mean_error: float
    std_error: float
    max_abs_error: float
    confidence: float
    feature_importance: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "feature": self.feature,
            "mean_error": self.mean_error,
            "std_error": self.std_error,
            "max_abs_error": self.max_abs_error,
            "confidence": self.confidence,
            "feature_importance": self.feature_importance,
        }


@dataclass
class DetectionResult:
    """Complete output of the error detection algorithm."""

    primary_error: ErrorScore
    ranked_errors: List[ErrorScore]
    alignment: List[tuple[int, int]]
    per_frame_differences: List[AlignedDifference]
    reference_motion: CanonicalMotion
    human_motion: CanonicalMotion
    timing_error: float = 0.0

    def summary(self) -> Dict[str, object]:
        return {
            "primary_error": self.primary_error.to_dict(),
            "all_errors": [e.to_dict() for e in self.ranked_errors],
            "alignment_length": len(self.alignment),
            "reference_frames": len(self.reference_motion),
            "human_frames": len(self.human_motion),
            "timing_error_sec": round(self.timing_error, 4),
        }
