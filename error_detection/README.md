# Error Detection Algorithm

Compare a **human annotated video motion** with a **robot reference motion** and detect the most significant semantic differences.

## What it does

1. **Load** two canonical motion sequences (human attempt + robot reference).
2. **Align** them temporally with Dynamic Time Warping (DTW).
   - Feature distances are **range-normalized** so elevation, azimuth, and
     torso angles contribute fairly.
   - **Circular wrap-around** is handled for azimuth/yaw (e.g. 359° vs 1° is
     2°, not 358°).
3. **Compute** per-feature differences in a shared canonical pose space.
4. **Rank** errors by magnitude, importance, and consistency.
5. **Output** the primary error **and a rhythm/timing error** (mean aligned
   timestamp lag), e.g.:

```json
{
  "feature": "right_arm_elevation",
  "max_abs_error": 88.76,
  "confidence": 0.553
}
```

## Canonical features

- `left_arm_elevation`, `right_arm_elevation`
- `left_arm_azimuth`, `right_arm_azimuth`
- `left_elbow_flexion`, `right_elbow_flexion`
- `torso_yaw`
- `torso_lean`

## Usage

### Python API

```python
from error_detection.detector import ErrorDetector
from error_detection.loader import load_canonical_motion

reference = load_canonical_motion("demo_output/reference_motion.json", source="robot")
human = load_canonical_motion("demo_output/human_motion.json", source="human")

detector = ErrorDetector()
result = detector.detect(human, reference)

print(result.primary_error.feature)
print(result.primary_error.max_abs_error)
print(result.summary())
```

### CLI

```bash
python -m error_detection.cli \
  --human demo_output/human_motion.json \
  --reference demo_output/reference_motion.json \
  --output error_detection_output/result.json
```

### Demo scenarios

Run synthetic examples across multiple error types:

```bash
python error_detection/demo_scenarios.py
```

This generates a report and writes per-scenario JSON files to
`error_detection_output/demos/`.

### Frontend visualizer

A Plotly-based visualizer is included at `error_detection/frontend/index.html`.
It loads any result JSON and shows:

- Primary error card
- Bar chart of all ranked errors
- DTW alignment path

Serve it locally from the repo root:

```bash
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/error_detection/frontend/index.html
```

## Output format

`result.json` contains:

- `primary_error`: the single most important detected error.
- `ranked_errors`: all features ranked by severity × importance × confidence.
- `alignment`: DTW frame-to-frame index pairs.
- `summary`: high-level counts and statistics.

## Folder structure

```
error_detection/
├── __init__.py        # public API exports
├── models.py          # CanonicalPose, CanonicalMotion, ErrorScore, ...
├── loader.py          # JSON load/save helpers
├── alignment.py       # DTW alignment
├── difference.py      # per-feature difference engine
├── ranker.py          # error ranking and primary-error selection
├── detector.py        # top-level ErrorDetector
├── cli.py             # command-line entry point
├── demo_scenarios.py  # synthetic test cases
├── frontend/
│   └── index.html     # Plotly-based result visualizer
├── requirements.txt   # minimal dependencies
└── README.md          # this file
```

## Research-backed recent updates

Based on recent work on cross-embodiment motion comparison and human-robot
motion correspondence:

- **Circular-aware distance** — angular features such as azimuth and torso yaw
  now use shortest-path wrap-around in both the DTW cost matrix and the
  difference engine. This avoids the 359° vs 1° = 358° bug.
- **Range-normalized DTW** — each feature is divided by its typical range before
  distance computation, so azimuth (0-360°) no longer dominates elevation
  (0-180°).
- **Rhythm / timing error** — the mean timestamp lag across aligned frames is
  now reported as `timing_error_sec`, useful for detecting "human performed the
  move too slowly" even when the shape is correct.

Papers that motivated these changes:

- _Assessing Similarity Measures for the Evaluation of Human-Robot Motion
  Correspondence_ (2024) — recommends Gromov DTW and other heterogeneous
  time-series similarity measures for human-robot correspondence evaluation.
- _Motion Similarity Evaluation between Human and a Tri-Co Robot during
  Real-Time Imitation with a Trajectory Dynamic Time Warping Model_ (Sensors 2022) — applies DTW to evaluate human-robot motion similarity under timing
  drift.
- _AdaMorph: Unified Motion Retargeting via Embodiment-Aware Adaptive
  Transformers_ (2025) — advocates canonical base-frame representations and
  6-D/rotation-based features to avoid Euler-angle discontinuities.

Future upgrades to consider when human video data arrives:

- Replace scalar canonical angles with pelvis-rooted 3-D positions + 6-D
  limb rotations.
- Add pose-estimation confidence as a per-frame weight.
- Add simple physical feasibility checks (joint limits, self-collision) so
  MIRROR only demonstrates errors G1 can actually perform.

## Integration with body_mirror

This package mirrors the canonical pose model and difference logic used in
`body_mirror/motion/` but is self-contained so it can be used independently on
annotated video outputs without importing the full robot runtime stack.
