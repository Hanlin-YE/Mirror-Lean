#!/usr/bin/env python3
"""Run the error detector across multiple synthetic demo scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np

from error_detection.detector import ErrorDetector
from error_detection.loader import save_result
from error_detection.models import CanonicalMotion, CanonicalPose


DEMO_DIR = Path(__file__).resolve().parent.parent / "error_detection_output" / "demos"


@dataclass
class Scenario:
    name: str
    reference: CanonicalMotion
    human: CanonicalMotion


def _make_sine_motion(
    feature: str,
    amplitude: float,
    offset: float,
    duration: float = 2.0,
    fps: float = 30.0,
) -> CanonicalMotion:
    """Generate a simple sinusoidal reference motion for one dominant feature."""
    frames = int(duration * fps)
    poses: List[CanonicalPose] = []
    for i in range(frames):
        t = i / fps
        kwargs: Dict[str, float] = {
            "timestamp": t,
            "left_arm_elevation": 20.0,
            "right_arm_elevation": 20.0,
            "left_arm_azimuth": 90.0,
            "right_arm_azimuth": 90.0,
            "left_elbow_flexion": 90.0,
            "right_elbow_flexion": 90.0,
            "torso_yaw": 0.0,
            "torso_lean": 0.0,
        }
        kwargs[feature] = offset + amplitude * np.sin(2 * np.pi * 0.5 * t)
        poses.append(CanonicalPose(**kwargs))
    return CanonicalMotion(poses=poses, source="reference")


def scenario_perfect_mimic() -> Scenario:
    motion = _make_sine_motion("right_arm_elevation", 40.0, 60.0)
    return Scenario("perfect_mimic", motion, motion)


def scenario_right_arm_too_low() -> Scenario:
    reference = _make_sine_motion("right_arm_elevation", 40.0, 60.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["right_arm_elevation"] -= 30.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("right_arm_too_low", reference, human)


def scenario_left_arm_forward() -> Scenario:
    reference = _make_sine_motion("left_arm_azimuth", 30.0, 90.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["left_arm_azimuth"] += 45.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("left_arm_forward", reference, human)


def scenario_elbow_bent() -> Scenario:
    reference = _make_sine_motion("right_elbow_flexion", 40.0, 120.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["right_elbow_flexion"] -= 35.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("right_elbow_bent", reference, human)


def scenario_torso_twisted() -> Scenario:
    reference = _make_sine_motion("torso_yaw", 20.0, 0.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["torso_yaw"] += 25.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("torso_twisted", reference, human)


def scenario_slow_human() -> Scenario:
    """Same motion shape but performed 30% slower (tests DTW timing robustness)."""
    reference = _make_sine_motion("right_arm_elevation", 40.0, 60.0, duration=2.0)
    slow_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["timestamp"] *= 1.3
        slow_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=slow_poses, source="human")
    return Scenario("slow_human", reference, human)


def scenario_multiple_errors() -> Scenario:
    reference = _make_sine_motion("right_arm_elevation", 40.0, 60.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        d["right_arm_elevation"] -= 20.0
        d["right_elbow_flexion"] -= 25.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("multiple_errors", reference, human)


def scenario_azimuth_wrap() -> Scenario:
    """Tests circular shortest-path error for azimuth crossing 0/360 boundary."""
    reference = _make_sine_motion("left_arm_azimuth", 30.0, 350.0)
    human_poses: List[CanonicalPose] = []
    for p in reference.poses:
        d = p.to_dict()
        # Add +10 degrees across the boundary; naive diff would be near 350.
        d["left_arm_azimuth"] = (d["left_arm_azimuth"] + 10.0) % 360.0
        human_poses.append(CanonicalPose(**d))
    human = CanonicalMotion(poses=human_poses, source="human")
    return Scenario("azimuth_wrap", reference, human)


SCENARIOS: List[Scenario] = [
    scenario_perfect_mimic(),
    scenario_right_arm_too_low(),
    scenario_left_arm_forward(),
    scenario_elbow_bent(),
    scenario_torso_twisted(),
    scenario_slow_human(),
    scenario_multiple_errors(),
    scenario_azimuth_wrap(),
]


def run_scenarios(output_dir: Path = DEMO_DIR) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    detector = ErrorDetector()
    report: List[Dict[str, object]] = []

    for scenario in SCENARIOS:
        result = detector.detect(scenario.human, scenario.reference)
        save_result(result, output_dir / f"{scenario.name}.json")
        report.append(
            {
                "scenario": scenario.name,
                "primary_feature": result.primary_error.feature,
                "max_abs_error": round(result.primary_error.max_abs_error, 3),
                "confidence": result.primary_error.confidence,
                "timing_error_sec": round(result.timing_error, 4),
                "ranked_top3": [
                    e.feature for e in result.ranked_errors[:3]
                ],
            }
        )

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(report, f, indent=2)

    return {"scenarios": report, "output_dir": str(output_dir)}


def print_report(report: Dict[str, object]) -> None:
    print("\nError Detection Demo Report")
    print("=" * 75)
    for row in report["scenarios"]:  # type: ignore[index]
        print(
            f"{row['scenario']:<20} "
            f"primary={row['primary_feature']:<25} "
            f"error={row['max_abs_error']:>7.2f}°  "
            f"conf={row['confidence']}  "
            f"timing={row['timing_error_sec']}s"
        )
        print(f"{'':20} top3={row['ranked_top3']}")
    print("=" * 75)
    print(f"Detailed results: {report['output_dir']}")


if __name__ == "__main__":
    report = run_scenarios()
    print_report(report)
