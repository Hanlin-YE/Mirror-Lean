#!/usr/bin/env python3
"""CLI to compare a human annotated video motion against a robot reference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from error_detection.detector import ErrorDetector
from error_detection.loader import load_canonical_motion, save_result


def main():
    parser = argparse.ArgumentParser(
        description="Detect errors between human and robot annotated motion sequences.",
    )
    parser.add_argument(
        "--human",
        required=True,
        help="Path to human canonical motion JSON (list of poses or {poses: [...]}).",
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Path to robot reference canonical motion JSON.",
    )
    parser.add_argument(
        "--output",
        default="./error_detection_output/result.json",
        help="Where to write the detection result JSON.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=180.0,
        help="Max error threshold used for confidence calibration (degrees).",
    )
    args = parser.parse_args()

    human_path = Path(args.human)
    reference_path = Path(args.reference)
    for p in (human_path, reference_path):
        if not p.exists():
            raise FileNotFoundError(f"Input not found: {p}")

    human_motion = load_canonical_motion(human_path, source="human")
    reference_motion = load_canonical_motion(reference_path, source="robot")

    detector = ErrorDetector(max_error_threshold=args.threshold)
    result = detector.detect(human_motion, reference_motion)

    save_result(result, args.output)

    print("Primary error:")
    print(json.dumps(result.primary_error.to_dict(), indent=2))
    print(f"\nFull result written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
