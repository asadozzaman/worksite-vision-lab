# Phase status

As of 2026-10-13 (Asia/Dhaka). This is a research prototype, not a finished safety platform.

| Phase | Status | Evidence / remaining gate |
|---|---|---|
| 0 — foundation | Implemented and verified, with documented provenance risks | Repository/push access, isolated model load, official-architecture match, actual classes, licensed video acquisition, tests and CI verified. Original weight training-data rights unaudited; weights not redistributed. |
| 1 — real detection baseline | Inference implemented and verified; reference evaluation partial | Two real clips, 298 frames, annotated videos, JSONL, CPU timing, repeatability and frame-linked qualitative failures. Human reference annotations/accuracy pending. |
| 2 — tracking comparison | Implemented and verified with observational proxies; formal evaluation pending | Both trackers on both clips, person-only records/videos, 12 replays and repeatability. No human identity labels or formal scores. |
| 3 — failure analysis | Partially implemented and executed | Diagnostic variants, annotation/freeze tools and a tested person evaluation runner; human reference QA and actual accuracy comparisons pending. |
| 4 — event reliability | Not started | Needs validated association and frozen reference events. |
| 5 — API/dashboard | Not started | No mock application or invented metrics. |
| 6 — release validation | Not started | Requires full platform integration and end-to-end validation. |

## Phase 0

**Objective:** establish verified inputs and reproducible software before inference.

Delivered Python packaging, CLI diagnostics, validated config/provenance schemas,
bounded static checkpoint inspection, isolated loader, pinned dependencies, AGPL
license/notices, Windows/Linux CI and acquisition/annotation protocols. No private
or employer code/data was imported; SiteGuard application code was inspected only.

Checkpoint: 5,394,437 bytes, SHA-256
`b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`,
source commit `f4d1a097679439f3eaec4e5569d4e52d479cf592`. Restricted load succeeded
inside an offline non-root container. Actual 11 labels include Person at 6;
2,508,090 parameters; exact state-dict match to official YOLO26n with 11 classes.
Embedded producer version 8.4.37 and AGPL declaration are recorded. Original
training lineage/image rights remain unaudited; no weight redistribution.

Important finding: producer 8.4.37 defaults missing `_end2end` to true; current
8.4.173 defaults false. The loader explicitly restores the producer behavior.
The initial false reading is retained as an investigated compatibility artifact.
Initial container mount `inspect.py` shadowed the standard library; renamed and
retested. Static inspection alone was never treated as safe-load certification.

Two suitable Commons inputs acquired (CC0 and CC BY 4.0), measured and sampled.
A third roof clip was rejected for insufficient PPE detail. Pexels source/license
research is complete but those files remain unacquired due to automatic collection
restrictions; Commons alternatives unblock the baseline.

## Phase 1

**Objective:** real construction-video inference before tuning or training.

Implemented normalization with source/output hashes and frame counts, audited
model reconstruction, CPU/optional-device detection CLI, streaming JSONL including
empty frames, aligned timestamps, annotated video, evidence samples, timing,
failure records and reproducible Docker wrapper. GPU path is implemented but not
executed; the image contains CPU Torch only.

| Executed run | Frames | Processing time | Processing FPS |
|---|---:|---:|---:|
| Building baseline | 131 | 56.690 s | 2.311 |
| Street baseline | 167 | 53.625 s | 3.114 |

Two-CPU/2 GiB Docker limit, two threads, 360×640 normalized inputs at 25 fps,
640 inference size, confidence 0.25. Processing includes decode/predict/draw/write,
excludes model load/warmup. Other host applications were active. No general
performance or accuracy claim follows from these runs.

All 298 JSONL indexes/timestamps and both video frame counts verified. Repeated
building inference produced byte-identical detection records. Sample review shows
missed people and suspected false helmet detections. No unique-worker, violation,
precision/recall/mAP or tracking score is claimed. Human reference annotations are
pending; assistant qualitative review is explicitly distinguished from ground truth.

Evidence: `experiments/results/`, `experiments/reports/BASELINE_CPU.md`,
`docs/evidence/`. Local binary artifacts: `data/runs/building-baseline/` and
`data/runs/street-baseline/`. See BASELINE_REPRODUCTION.md for exact commands.

## Phases 2 and 3

**Objective:** track people independently of gear, compare identical inputs and
investigate failures before safety-event logic.

Implemented persistent person-only ByteTrack/BoT-SORT adapters, hash-verified
offline detection replay, explicit configs, aligned JSONL/video, CPU/RSS sampling,
track lifetime/gap observations, artifact validation and raw-frame review export.
Every empty frame updates tracker state. Each video runs in its own process;
upstream process-global ID allocation prevents safe interleaved in-process streams.

Four baseline replays, four conf 0.10 replays, a no-GMC variant, a short-buffer
variant and two repeats completed: 1,824 tracking frames total. Two additional
real detector runs supplied lower-threshold inputs. All artifact hashes, timestamps
and decoded annotated-video lengths verified. Both street repeats are byte-identical.

Street no-track frames: ByteTrack 112/167 and BoT-SORT 104/167 at conf 0.25; both 97/167
at conf 0.10. No accuracy conclusion follows. Observed duplicate IDs 32/33 at street
frame 125 overlap one visible worker; input also has overlapping detector boxes.
Three predeclared diagnostic changes and contrary/ambiguous findings are preserved.

Evidence: `experiments/reports/TRACKING_COMPARISON.md`, `experiments/results/tracking/`,
and local `data/tracking/`. All 298 source frames are exported for review under
`data/review/`; templates remain explicitly unreviewed. Browser navigation, overlay
switching and timestamp alignment tested. Review control event bug fixed/rechecked.

Limitations: no human reference identities, formal ID-switch/IDF1/HOTA/MOTA scores,
event truth, or reliability improvement. Clips are development data; a separate
held-out source is still needed. CPU timings vary with host load and exclude
detector inference during replay. No GPU execution or training.

## Tests and external execution

54 foundation tests pass locally on Windows/Python 3.10; vision integration is
skipped in the lightweight environment. The separate 17-test tracking suite passes
on Windows/Python 3.10 and Linux Docker/Python 3.11, including replay alignment,
checksum rejection, existing-output protection and truncated-input failure records.
Ten validation tests overlap both suites; these are not 71 distinct tests.
Ruff lint/format pass. Foundation
editable install, wheel build and dependency check passed. Actual FFmpeg integration
uses a labeled synthetic software fixture, excluded from research evaluation.
Six-job Windows/Linux Python 3.10–3.12 Actions matrices passed for commits
`0ea80032e0560af04681f62a9e0a38ec8de97066` and
`1fcc2c8f6dd3d9f3a4922e4e7356ad063b7e140a`.
Detection baseline commit `623489424847fbbee6cf606d24b6d6370d9d4368` passed both
push and PR CI matrices. Tracking implementation commit
`7b6b8841731e15000bd7112cc10c4cbe52872207` passed both seven-job workflows,
including the new tracker integration job. See PR checks for current-head status.

GitHub: authenticated push permission verified for `asadozzaman/worksite-vision-lab`.
The new repository had no history. Empty base commit `a5f8ce3` initializes main;
foundation, detection and tracking were merged through
[PR #1](https://github.com/asadozzaman/worksite-vision-lab/pull/1) with explicit user
approval. The squash commit on main is `e1eefd9052c4fb74a617d9ca01968bfccdfa4762`.
The next annotation workflow is developed separately on `feat/reference-annotation-workflow`.
Implementation commit: `fea452b`. Review: [PR #2](https://github.com/asadozzaman/worksite-vision-lab/pull/2),
open for review; no merge of this new work has been performed.

No Kaggle connector/execution action was exposed when checked; discovery returned
no Kaggle result. No hosted notebook, GPU job, training or external paid compute ran.

## Changed files and next actions

Foundation: `vision/`, `tests/`, `scripts/`, `docker/`, `requirements/`, configs,
CI, README, license/notices and docs. Baseline additions: `vision/detection/`,
normalization/Docker run scripts, detection-record tests, measured structured
results and evidence reports. Checkpoints, videos, credentials and private assets
remain excluded from Git.

Tracking additions: `vision/tracking/`, `vision/evaluation/`, replay/review/validation
scripts, Docker layer, tracker configs/tests, measured results and comparison report.
The person annotation editor adds source-bound v2 JSON, independent manual IDs,
copy/edit/undo, explicit empty-frame confirmation, human review attestation and
reference freeze commands. New bundles cover all 298 frames under `data/annotation/`.
The browser test labels are marked software fixtures and are not human truth.
The new local foundation suite passes 79 tests (25 new), with seven Node tests;
see [workflow and verification](ANNOTATION_WORKFLOW.md). Current-head CI is reported
by the separate annotation pull request.

Next: human review of the exported contiguous reference frames, frozen identity
and box annotations, and a distinct held-out scene. Use these to evaluate detector
duplicates/person fallback before PPE association or alert tuning. No training is justified.
Do not claim later phases complete until their code and experiments actually run.

The new evaluation branch `codex/person-reference-evaluation` builds on the unmerged
annotation branch. It provides `evaluate-person` with frozen-source checks, detector
P/R/F1, motmetrics IDF1/MOTA/switch/fragmentation results, and frame-linked diagnostics.
See [protocol and implementation limits](PERSON_EVALUATION.md). Software fixture
scores are excluded from real-video research claims. No new checkpoint inference,
human annotation, accuracy-based tuning, event code or model training occurred.
Local evaluation environment: 138 repository tests passed; vision integration is
handled separately. Lightweight foundation: 103 passed, with numerical/vision
modules intentionally skipped. Seven Node tests, Ruff lint/format, dependency
checks and wheel build passed. Fourteen non-benchmark upstream metric-function
tests passed; the legacy multi-sequence helper is outside the supported scope.
The CLI rejected the actual unreviewed building template and created no result.
Evaluation implementation commit: `4a94fd5`; [PR #3](https://github.com/asadozzaman/worksite-vision-lab/pull/3).
This PR targets the annotation branch and depends on PR #2. Both remain unmerged;
current-head GitHub checks are the source of CI status.
