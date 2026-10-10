# Phase status

As of 2026-10-10 (Asia/Dhaka). This is a research prototype, not a finished safety platform.

| Phase | Status | Evidence / remaining gate |
|---|---|---|
| 0 — foundation | Implemented and verified, with documented provenance risks | Repository/push access, isolated model load, official-architecture match, actual classes, licensed video acquisition, tests and CI verified. Original weight training-data rights unaudited; weights not redistributed. |
| 1 — real detection baseline | Inference implemented and verified; reference evaluation partial | Two real clips, 298 frames, annotated videos, JSONL, CPU timing, repeatability and frame-linked qualitative failures. Human reference annotations/accuracy pending. |
| 2 — tracking comparison | Not started | Next: person-only ByteTrack/BoT-SORT; distinguish detector misses from tracker errors. Human identity labels needed for formal scores. |
| 3 — failure analysis | Partially implemented | Initial frame-linked observations and three untested hypotheses recorded; no controlled tuning experiments yet. |
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

## Tests and external execution

44 tests pass locally on Windows/Python 3.10; Ruff lint/format pass. Foundation
editable install, wheel build and dependency check passed. Actual FFmpeg integration
uses a labeled synthetic software fixture, excluded from research evaluation.
Six-job Windows/Linux Python 3.10–3.12 Actions matrices passed for commits
`0ea80032e0560af04681f62a9e0a38ec8de97066` and
`1fcc2c8f6dd3d9f3a4922e4e7356ad063b7e140a`.
Current baseline changes require their own Actions run; see PR checks for latest status.

GitHub: authenticated push permission verified for `asadozzaman/worksite-vision-lab`.
The new repository had no history. Empty base commit `a5f8ce3` initializes main;
implementation lives on `feat/phase-0-foundation`.
[PR #1](https://github.com/asadozzaman/worksite-vision-lab/pull/1) is open and unmerged.
The PR head/history records subsequent baseline commit SHAs without a self-referential
commit ID in this file.

No Kaggle connector/execution action was exposed when checked; discovery returned
no Kaggle result. No hosted notebook, GPU job, training or external paid compute ran.

## Changed files and next actions

Foundation: `vision/`, `tests/`, `scripts/`, `docker/`, `requirements/`, configs,
CI, README, license/notices and docs. Baseline additions: `vision/detection/`,
normalization/Docker run scripts, detection-record tests, measured structured
results and evidence reports. Checkpoints, videos, credentials and private assets
remain excluded from Git.

Next: obtain human review of the frame-linked reference subset, then compare
person-only trackers on frozen inputs. Investigate official person-detector fallback
before attributing missing detections to tracking. No training is currently justified.
Do not claim later phases complete until their code and experiments actually run.
