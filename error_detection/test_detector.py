#!/usr/bin/env python3
"""Quick sanity tests for the error detection package."""

from __future__ import annotations

import json
from pathlib import Path

from error_detection.detector import ErrorDetector
from error_detection.loader import load_canonical_motion, save_result
from error_detection.models import CanonicalMotion, CanonicalPose


def test_synthetic_motion():
    """Two identical motions should produce near-zero primary error."""
    poses = [
        CanonicalPose(timestamp=i / 30.0, right_arm_elevation=45.0)
        for i in range(10)
    ]
    motion = CanonicalMotion(poses=poses, source="test")

    detector = ErrorDetector()
    result = detector.detect(motion, motion)

    assert result.primary_error.max_abs_error < 1e-6
    print("PASS: identical motions -> zero error")


def test_offset_motion():
    """A constant offset on one feature should be detected as primary error."""
    ref_poses = [
        CanonicalPose(timestamp=i / 30.0, right_arm_elevation=45.0)
        for i in range(10)
    ]
    human_poses = [
        CanonicalPose(timestamp=i / 30.0, right_arm_elevation=15.0)
        for i in range(10)
    ]
    reference = CanonicalMotion(poses=ref_poses, source="robot")
    human = CanonicalMotion(poses=human_poses, source="human")

    detector = ErrorDetector()
    result = detector.detect(human, reference)

    assert result.primary_error.feature == "right_arm_elevation"
    assert abs(result.primary_error.max_abs_error - 30.0) < 1e-3
    print("PASS: offset right_arm_elevation detected")


def test_demo_files():
    """Run detection on the existing demo_output files."""
    root = Path(__file__).resolve().parent.parent / "demo_output"
    human = load_canonical_motion(root / "human_motion.json", source="human")
    reference = load_canonical_motion(root / "reference_motion.json", source="robot")

    detector = ErrorDetector()
    result = detector.detect(human, reference)

    print("Primary error:")
    print(json.dumps(result.primary_error.to_dict(), indent=2))

    out_dir = Path("error_detection_output")
    out_dir.mkdir(exist_ok=True)
    save_result(result, out_dir / "result.json")
    print(f"Saved result to {out_dir / 'result.json'}")


if __name__ == "__main__":
    test_synthetic_motion()
    test_offset_motion()
    test_demo_files()
