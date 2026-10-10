# Implementation plan

Reviewed 2026-10-10 (Asia/Dhaka). Follow Research → Design → Implement → Test →
Measure → Analyze → Document → Commit. Each gate needs execution evidence.

| Phase | Scope | Acceptance gate |
|---|---|---|
| 0 | Repository, pinned environment, provenance, checkpoint research, CI | Correct repository/history and access verified; foundation checks pass; isolated checkpoint compatibility evidence; licensing and video acquisition status explicit. Baseline model and real input confirmed before Phase 1. |
| 1 | Video normalization and streaming detection CLI | Actual construction video decoded and inferred on CPU; annotations, per-frame JSONL/CSV, timestamps, checksums, versions and throughput saved; reviewed frames and failures documented. No claimed accuracy without trustworthy labels. |
| 2 | Person-only ByteTrack and BoT-SORT | Same detections/input/settings/hardware; independent tracker state per video; both result videos and tracking records inspected; reviewed identity subset or explicitly labeled proxies. |
| 3 | Failure evidence and controlled experiments | Frame-linked failure records; three hypotheses based on observed failures; frozen reference set; comparable original/modified runs and negative results saved. |
| 4 | Geometric PPE association and temporal safety rules | Unknown/ambiguous states preserved; tested event lifecycle and occlusion behavior; comparison of immediate, consecutive, voting, confidence-aware and worker-aware methods against event annotations. No improvement claim without measured support. |
| 5 | FastAPI, SQLite jobs and React dashboard | Real upload-to-result flow, playback aligned to timestamps, evidence/review/export and all six requested pages; bounded safe uploads; local-file isolation; no decorative metrics; responsive and accessible states checked. |
| 6 | Reproduction and release readiness | CPU demonstration works from documented setup; tests/build/start checks pass; real CI status and commit/PR recorded; no assets or secrets in Git; limitations and real screenshots/results documented. |

## Architecture decisions

- Start with small CPU runs at 640 pixels, batch 1. Measure before optimizing.
- Keep original video and create one normalized constant-frame-rate derivative per
  source. Record both hashes, exact FFmpeg command, dimensions and frame timestamps.
- Detection records will include experiment ID, frame index, timestamp, class ID and
  name, confidence and original-input-coordinate box. Store empty frames too.
- Feed only the resolved person class into each tracker while retaining all PPE
  detections for later association. Keep tracking and PPE inference separable.
- Use head/torso regions, overlap, competing assignments and temporal continuity;
  ambiguous gear stays unknown. Class `none` is not automatically missing vest.
- Single local background worker initially; SQLite owns job/event state. No Redis
  or distributed orchestration until workload evidence requires it.
- Bind the initial application to localhost. Uploaded names never become paths;
  use server-generated IDs and check resolved paths inside the data root.
- Browser pages consume actual stored runs. A blank database shows empty states.

## Experiment protocol

Split by source clip/camera, not random adjacent frames. Reserve a frozen test set
before tuning. Label worker boxes, visible PPE, visibility/uncertainty, video-local
identities and event intervals. Preserve annotation versions and reviewer notes.
Document precision/recall IoU, confidence and matching rules; use established metric
implementations for mAP and formal tracking scores when labels suffice. Never
estimate ID switches by treating model outputs as truth.

Before each experiment: state hypothesis, controlled variables, evaluation subset,
success criterion and resource budget. Preserve failures and outputs. Research
smoke tests with synthetic arrays are explicitly excluded from video evaluation.

## GitHub and Kaggle

Inspect existing history before mutation. Use `feat/phase-0-foundation`, commit
reviewed changes, push only tested work, and open a PR without merging. Record
actual Actions results separately from local results. An empty repository needs
an initial base commit before a PR is possible.

No Kaggle connector or execution action was exposed, and plugin discovery returned
no Kaggle result. GPU availability is unverified. Prepare hosted reproduction only
when a licensed input and baseline make it useful; do not upload uncertain assets
or train merely to demonstrate cloud use.
