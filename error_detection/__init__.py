"""Error detection for human-vs-robot annotated video comparison.

This package compares two temporally-aligned canonical motion sequences
(e.g. a human attempt and a robot reference) and detects the most
significant semantic differences.
"""

from error_detection.detector import ErrorDetector, DetectionResult
from error_detection.loader import load_canonical_motion, save_result
from error_detection.models import CanonicalMotion, CanonicalPose, ErrorScore

__all__ = [
    "ErrorDetector",
    "DetectionResult",
    "load_canonical_motion",
    "save_result",
    "CanonicalMotion",
    "CanonicalPose",
    "ErrorScore",
]
