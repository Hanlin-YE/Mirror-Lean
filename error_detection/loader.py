"""Load and save canonical motion data and detection results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from error_detection.models import CanonicalMotion, CanonicalPose, DetectionResult


def load_canonical_motion(path: str | Path, source: str = "unknown") -> CanonicalMotion:
    """Load a canonical motion sequence from JSON.

    The JSON may be either a list of pose dictionaries or an object with
    a ``poses`` key.
    """
    path = Path(path)
    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data, dict):
        raw_poses = data.get("poses", [data])
        source = data.get("source", source)
    else:
        raw_poses = data

    poses: List[CanonicalPose] = []
    for raw in raw_poses:
        timestamp = float(raw.get("timestamp", 0.0))
        kwargs = {f: float(raw.get(f, 0.0)) for f in CanonicalPose.__dataclass_fields__ if f != "timestamp"}
        poses.append(CanonicalPose(timestamp=timestamp, **kwargs))

    return CanonicalMotion(poses=poses, source=source)


def save_result(result: DetectionResult, output_path: str | Path) -> None:
    """Persist a detection result to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "primary_error": result.primary_error.to_dict(),
        "ranked_errors": [e.to_dict() for e in result.ranked_errors],
        "alignment": [list(pair) for pair in result.alignment],
        "timing_error_sec": round(result.timing_error, 4),
        "summary": result.summary(),
    }

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


def load_result(path: str | Path) -> Dict[str, object]:
    """Load a previously saved detection result."""
    with open(path, "r") as f:
        return json.load(f)
