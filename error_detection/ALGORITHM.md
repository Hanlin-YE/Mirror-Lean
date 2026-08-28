# Body Mirror / Error Detection Algorithm

This document describes the comparison, difference-checking, and error-ranking algorithm used by Body Mirror and the standalone `error_detection` package.

## 1. Problem statement

We need to compare a **human demonstration** with a **robot reference motion** even though:

- Human and robot morphologies differ.
- The human video may not exist yet, or may be temporally misaligned with the robot demo.
- Raw joint angles are not directly comparable.

The central design decision is to project both motions into a shared **canonical motion space** and compare there.

## 2. Canonical motion space

Both human and robot poses are converted to the same set of morphology-independent features:

| Feature | Meaning |
| --- | --- |
| `left_arm_elevation` | Angle of the left upper arm above horizontal |
| `right_arm_elevation` | Angle of the right upper arm above horizontal |
| `left_arm_azimuth` | Horizontal orientation of the left arm |
| `right_arm_azimuth` | Horizontal orientation of the right arm |
| `left_elbow_flexion` | Left elbow bend angle |
| `right_elbow_flexion` | Right elbow bend angle |
| `torso_yaw` | Torso rotation around vertical axis |
| `torso_lean` | Torso forward/backward lean |

For the robot, these values come from forward kinematics of the Unitree G1.
For the human, they are derived from a pose estimator (MediaPipe / YOLO-pose) and normalised into the same units.

## 3. Pipeline overview

```text
Robot reference motion ──┐
                         ├──▶ CanonicalPose sequences ──▶ DTW alignment ──▶ Difference engine ──▶ Error ranker
Human attempt motion ────┘
```

### 3.1 Temporal alignment — Dynamic Time Warping (DTW)

Because the human and robot may perform the same motion at different speeds, we do **not** compare frame `i` to frame `i`. Instead we find the optimal non-linear alignment between the two sequences.

The DTW cost between two frames is computed with three recent improvements:

1. **Range normalisation**: each feature is divided by its typical range before distance computation, so azimuth (0-360°) does not dominate elevation (0-180°).
2. **Circular-aware distance**: for `*_arm_azimuth` and `torso_yaw`, the distance uses shortest-path wrap-around, so 359° vs 1° is 2° instead of 358°.
3. **Per-feature weights**: optional importance weights can emphasise or de-emphasise particular joints.

### 3.2 Difference engine

After alignment, every paired frame produces a `FeatureDelta`:

```text
error      = human_value - ref_value
abs_error  = |error|
```

For circular features the error is wrapped to `[-180, 180)` before the absolute value is taken.

### 3.3 Error ranker

Errors are aggregated per feature across the whole aligned sequence:

```text
mean_error     = mean(error per frame)
std_error      = standard deviation of error
max_abs_error  = maximum absolute error
```

Confidence is computed from:

```text
significance  = clamp(max_abs_error / max_error_threshold, 0, 1)
consistency   = 1 - clamp(std_error / (max_error_threshold / 2), 0, 1)
confidence    = 0.6 * significance + 0.4 * consistency
```

The final ranking score is:

```text
score = max_abs_error * feature_importance * confidence
```

The feature with the highest score becomes the **primary error**.

### 3.4 Rhythm / timing error

The mean absolute timestamp lag across aligned frame pairs is reported as `timing_error_sec`. A high value means the human performed the right motion shape but at the wrong speed or with the wrong timing.

## 4. What we output

```json
{
  "primary_error": {
    "feature": "right_arm_elevation",
    "mean_error": 37.64,
    "std_error": 32.04,
    "max_abs_error": 88.76,
    "confidence": 0.553,
    "feature_importance": 1.0
  },
  "ranked_errors": [...],
  "alignment": [[0, 0], [1, 1], ...],
  "timing_error_sec": 0.1255
}
```

## 5. When no human video is available

The pipeline still works with a synthetic human motion by adding a configurable angular offset to the robot reference. This lets us:

- Validate the difference engine and ranking logic.
- Generate demo outputs for the frontend.
- Prepare MIRROR/MORPH stages without waiting for real human data.

When a real human video arrives, only the input conversion step changes; the comparison pipeline stays the same.

## 6. Research basis

Recent improvements were informed by the following work:

- **Assessing Similarity Measures for Human-Robot Motion Correspondence** (2024) — recommends Gromov DTW and other heterogeneous time-series similarity measures for cross-embodiment comparison.
- **Motion Similarity Evaluation via Trajectory Dynamic Time Warping** (Sensors 2022) — applies DTW to evaluate human-robot motion similarity under timing drift.
- **AdaMorph: Unified Motion Retargeting via Embodiment-Aware Adaptive Transformers** (2025) — motivates moving from scalar Euler angles to pelvis-rooted 3-D positions and 6-D rotation representations.

## 7. Future upgrades

- Replace scalar canonical angles with pelvis-rooted positions + 6-D limb rotations.
- Add Gromov DTW as an optional alignment backend.
- Use pose-estimation confidence as a per-frame weight.
- Add physical feasibility checks (joint limits, self-collision) so MIRROR only demonstrates errors G1 can actually perform.

## 8. Usage

### Python API

```python
from error_detection.detector import ErrorDetector
from error_detection.loader import load_canonical_motion

reference = load_canonical_motion("demo_output/reference_motion.json", source="robot")
human = load_canonical_motion("demo_output/human_motion.json", source="human")

detector = ErrorDetector()
result = detector.detect(human, reference)
print(result.primary_error.feature, result.primary_error.max_abs_error)
```

### CLI

```bash
PYTHONPATH=. python -m error_detection.cli \
  --reference demo_output/reference_motion.json \
  --human demo_output/human_motion.json \
  --output error_detection_output/result.json
```

### Frontend visualiser

```bash
# Error detection visualiser (port 8083)
python -m http.server 8083 --directory error_detection/frontend

# Body Mirror app (port 8001)
python -m body_mirror.app.main
```
