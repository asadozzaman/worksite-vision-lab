# Person detection and tracking evaluation

The runner compares one detector run with **one ByteTrack and one BoT-SORT run**
against the same frozen person-reference interval. It works offline without loading
a checkpoint, decoding inference video, or installing the vision stack. It outputs
precision/recall/F1, IDF1, MOTA, mean matched IoU, CLEAR switches and fragmentation.
It does not compute mAP, HOTA, PPE or safety-event metrics.

**Current evidence:** implementation and synthetic software checks completed;
real-video accuracy remains unmeasured because no human-reviewed reference is available.
Tests and fixture numbers must never be presented as construction-video results.

## Install and run

Use a separate environment to keep numerical metric dependencies distinct from
the foundation and model runtime. Tested locally on Windows/Python 3.10; the
dedicated CI job covers Linux/Python 3.11 and Windows/Python 3.12.

```powershell
py -3.10 -m venv .venv-evaluation
.\.venv-evaluation\Scripts\python.exe -m pip install -r requirements/evaluation.lock.txt
.\.venv-evaluation\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv-evaluation\Scripts\python.exe -m pip check
```

First complete the [annotation workflow](ANNOTATION_WORKFLOW.md). Every selected
frame must be reviewed, including explicitly confirmed empty frames. Record
occlusion, uncertainty and exclusion reasons, independently check identity
continuity, declare human review, and freeze an annotation version. Freeze records
a declaration; it cannot authenticate a reviewer or independently establish truth.

Once the reference exists, run from the repository root:

```powershell
.\.venv-evaluation\Scripts\worksite.exe evaluate-person --reference data/references/building-v1 --images data/annotation/building/images --video data/normalized/building.mp4 --baseline data/runs/building-baseline --tracking data/tracking/building-bytetrack data/tracking/building-botsort --config experiments/configs/person-evaluation.json --output data/evaluation/building-v1-baseline
```

The named `building-v1` reference is a future input, not a delivered human label set.
Use your actual freeze directory. Output must be a new directory. Linux equivalents
use `.venv-evaluation/bin/python` and `.venv-evaluation/bin/worksite`.

## Integrity and comparison gates

- Recheck the exact annotation and manifest byte hashes against `freeze.json`,
  review interval, version/reviewer, declaration, counts and every source JPEG hash.
- Recheck the supplied normalized video SHA-256. The exporter previously established
  the raw-frame mapping. Evaluation verifies frozen hashes; it does not rerun inference.
- Require completed prediction runs and matching video, dimensions, frame rate,
  frame count and resolved Person class. Manual IDs are independent of model IDs.
- Both trackers must bind to the exact same detector JSONL **and baseline-summary
  bytes**, model metadata and detector parameters. Different detector inputs require
  separate comparisons; confidence variants cannot be silently mixed.
- Parse and hash the same prediction bytes. Verify every frame of the full streams,
  including frames outside the scored interval. Check indexes/timestamps, finite
  geometry/confidence, person class, source detection index/confidence, and unique
  track IDs/source detections within a frame. Records are bounded to 8 MiB per line.
- Score only the frozen contiguous interval. Start fresh metric state at its first
  frame; switches before/after the interval are outside this evaluation.
- Stage output privately until all streams and checksums pass. Reserve the output
  directory without overwriting, and publish the completed summary last. An interrupted
  publication without `comparison.json` is incomplete and must not be treated as a run.

Annotations can be evaluated against new predictions on the same video. The annotation
manifest's original model-overlay hashes remain in the report for provenance; they
do not force tuning to use only those predictions. Record any label changes or test-set
reuse externally. Both current clips are development scenes, not independent final tests.

## Matching and denominators

Default protocol is versioned in `experiments/configs/person-evaluation.json`:
IoU threshold 0.5, ignore IoA threshold 0.5, detector confidence at least 0.25.
Thresholds are inclusive. These are declared baseline evaluation settings, not an
accuracy-selected optimum.

**Detection:** retain Person boxes at/above the evaluation confidence. This setting
cannot be below the stored detector confidence floor because discarded boxes cannot
be recovered. Use maximum eligible one-to-one match count, then maximum total IoU.
One truth box can explain one prediction; duplicate eligible boxes remain false
positives. Unmatched truth is a false negative. This fixed-threshold assignment is
custom and differs from confidence-greedy COCO AP matching.

**Tracking:** use all emitted person tracks, without an extra confidence filter.
Clip Kalman boxes to image boundaries for scoring; retain boxes that clip to zero
area as unmatched predictions rather than dropping them. Feed `1 − IoU` distances
to pinned `motmetrics`, with below-threshold candidates marked ineligible. Its CLEAR
assignment preserves feasible previous matches, then assigns remaining pairs.
Its global identity assignment computes IDTP/IDFP/IDFN and IDF1 separately. A switch
can count when a previously matched person reappears with a new ID: switch memory
has no gap limit within the selected interval. Fragmentation follows the upstream
tracked–missed–tracked definition over reference observations.

**Exclusions:** ignored person boxes do not enter truth denominators. A prediction
is excluded only when its intersection divided by its own clipped area meets the
ignore threshold **and** its IoU with every valid person is below the matching
threshold. Multiple predictions can be covered by one ignored box. A prediction
eligible for a valid person stays scored, protecting crowded people and duplicates
from being hidden by nearby exclusions. Report both ignored labels and excluded
predictions. Zero-area predictions have zero IoA and cannot be excluded this way.

**Ratios:** precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN).
Zero denominators produce JSON `null` and blank CSV cells. A confirmed empty interval
still reports false positives, but has null MOTA and identity ratios. MOTA may be
negative. `motp` is mean matched IoU distance (lower is better);
`mean_matched_iou = 1 − motp`. Ratios use 0–1 values, not percentages.

This is a person-only custom protocol. It is not an official MOTChallenge benchmark
submission, a unique-worker estimate, or a safety-certification score. Short reviewed
intervals yield descriptive subset results; report their denominators and limitations.

## Outputs

- `comparison.json`: detector/tracker metrics, interval, counts, exclusions, full
  policy, source/config hashes, code hashes, dependency versions and metric-source hashes.
- `frames.jsonl`: each evaluated frame's matches, misses, false positives, exclusions
  and identity switches. Detection indexes refer to the original JSONL indexes;
  switches include the previous/current tracker IDs. Use this with the raw-frame viewer.
- `metrics.csv`: compact comparison; tracking-only fields are blank for detection.
- `report.md`: human-readable comparison with scope and metric interpretation.

No output is silently committed or shared. Labels, outputs, images and videos stay
under ignored `data/`. The summary hashes the three companion outputs; its own file
is not self-hashed. Checksums provide integrity evidence, not authenticated ownership.

## Verification and library boundary

Pinned motmetrics 1.4.0, NumPy 1.26.4, SciPy 1.15.3, pandas 2.3.3 and SciPy assignment.
Research: [released library documentation](https://pypi.org/project/motmetrics/1.4.0/),
[metric definitions](https://github.com/cheind/py-motmetrics/blob/v1.4.0/motmetrics/metrics.py),
and [accumulator semantics](https://github.com/cheind/py-motmetrics/blob/v1.4.0/motmetrics/mot.py).
Installed source hashes are recorded because release/tag code and later upstream
development must not be treated as interchangeable.

Software tests cover exact hand-calculated identity cases, stable/replaced IDs,
missed-frame fragmentation, reappearance after absence, continuity-preferred
matching, duplicate and ignore interactions, ambiguous matching, threshold boundaries,
empty/no-GT frames, clipping, filtered confidence, source corruption, selected
intervals, output protection and repeatability. Real prediction streams from eight
baseline/confidence-variant tracking runs passed the new parser and binding checks;
this compatibility check calculates **no real accuracy**.
Local Windows/Python 3.10 checks: 138 repository tests pass in the evaluation
environment, including 59 new evaluator tests. The targeted evaluation/reference
suite has 84 tests. The lightweight environment passes 103 tests and intentionally
skips optional numerical/vision suites. Seven existing Node tests, Ruff lint/format,
dependency checks and the wheel build also pass. The actual unreviewed building
template was rejected by the CLI without publishing a result directory.

An additional attempt to run the bundled upstream suites found obsolete pandas
test assertion/merge APIs and a missing optional benchmark-test plugin. The 14
non-benchmark upstream metric-function tests pass in this environment. The legacy
multi-sequence merge helper is unsupported and is not called by our runner. Do not
infer that every upstream API/test is compatible from this supported scoring path.
No dependency source or production globals are patched to conceal that limitation.

```powershell
.\.venv-evaluation\Scripts\python.exe -m pytest tests/test_evaluation_inputs.py tests/test_evaluation_metrics.py tests/test_evaluation_run.py tests/test_reference.py
.\.venv-evaluation\Scripts\python.exe -m pytest --pyargs motmetrics.tests.test_metrics -k "not benchmark"
```

Next research work is human person-reference QA and freezing, then actual quantitative
comparison. Use measured failures to decide on duplicate handling and person-detector
fallback. PPE association and temporal events remain subsequent phases.
