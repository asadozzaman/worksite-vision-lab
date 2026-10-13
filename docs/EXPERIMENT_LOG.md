# Experiment log

Real-video baseline runs are recorded below. No training, tracking benchmark or
event comparison has run. Synthetic software tests are excluded from evaluation.

## ENV-001 — foundation installation and checks

- Date: 2026-10-10, Asia/Dhaka.
- Hypothesis: a small Python-only foundation can validate provenance/settings and
  inspect checkpoint metadata without loading the CV stack.
- Environment: Windows, Python 3.10.10, isolated `.venv`, pinned foundation lock.
- First install failed because Hatchling editable installs with build isolation
  disabled require `editables`. Added and pinned `editables==0.5`; install passed.
- Initial archive-name regression failed on Windows because Python normalizes
  backslashes in ZIP names. Inspection now checks `ZipInfo.orig_filename`; this
  preserves the intended rejection on Windows and Linux.
- Local result: 31 tests passed in 0.39 s; Ruff lint/format passed; `pip check`
  reported no broken requirements. CLI asset and baseline configuration validation passed.
- These tests measure software behavior, not detection or safety accuracy.
- Follow-up: added a real FFmpeg/ffprobe integration test using a generated
  five-frame 64×48 software fixture, excluded from research data. All 32 local
  tests passed in 4.18 s; wheel build passed. Initial six-job GitHub CI matrix
  passed at commit `0ea80032e0560af04681f62a9e0a38ec8de97066` with 31 tests/job.

## MODEL-001 — static artifact inspection

- Input revision: SiteGuard `f4d1a097679439f3eaec4e5569d4e52d479cf592`.
- SHA-256: `b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`.
- Question: is the download an inspectable PyTorch ZIP rather than a pointer or HTML?
- Result: 5,394,437 bytes; 718 members; `data.pkl` 185,046 bytes; 74,135
  opcodes; 28 explicit globals and 0 dynamic globals. No model load performed.
- Interpretation: compatible archive structure and recognizable symbols; not
  proof of architecture, safe execution, licensing or accuracy.
- Evidence: [checkpoint-static.json](evidence/checkpoint-static.json).

## Next gated experiments

1. Isolated restricted load, exact official-architecture state-dict comparison,
   and synthetic compatibility smoke test. Record actual loaded names and outcome.
2. Review and normalize acquired real footage, then run a fixed CPU detection baseline.
3. Annotate observed failures before proposing or tuning three controlled hypotheses.

No failure hypotheses or performance improvements are claimed before observation.

## ASSET-001 — licensed footage acquisition and sampling

- Downloaded Commons `Men at work in building site.webm` (Akum20, CC0) and
  `Workers on the roof.webm` (Eric Harrison, CC BY-SA 2.0) through published links.
- Actual ffprobe outputs/hashes saved in `docs/evidence/commons-*-probe.json`.
- Inspected contact sheets sampled at one second and five seconds, respectively.
  First clip has a prominent worker and partially visible/background people;
  useful for a small qualitative test. Roof clip has insufficient worker/PPE detail
  and is rejected as primary evaluation footage. This is a documented failed
  candidate selection, not a detector failure.
- Reviewer: assistant visual inspection; no human identity or event annotations.
- No model inference on these files has occurred at this stage.

## MODEL-002 — isolated loading and producer-mode restoration

- Restricted load succeeded using the explicit class allowlist, no unrestricted
  fallback. Fresh official YOLO26n accepts every state-dict key/shape for 11 classes.
- Actual Person index 6; 2,508,090 parameters. Embedded AGPL and producer 8.4.37.
- Initial mount `inspect.py` shadowed Python's inspect module; failed before model
  load. Corrected to `model_check.py` and reran successfully.
- Raw object reported end2end false in 8.4.173. Source investigation showed
  8.4.37 used default true for the absent `_end2end` field. Restored explicitly,
  documented in loader/run metadata, and completed the compatibility smoke.
- This corrects the initial interpretation; it is not a claim of superior accuracy.

## BASELINE-001/002 — real-video CPU detection

- Inputs: CC0 building clip and CC BY 4.0 street-work clip; hashes in assets.json.
- Fixed configuration: 360×640 normalized CFR 25 fps, imgsz 640, confidence 0.25,
  original end-to-end mode, CPU/two threads, 2 GiB/two-CPU Docker limit.
- Building: 131 frames / 56.690 s = 2.311 processing FPS.
- Street: 167 frames / 53.625 s = 3.114 processing FPS.
- Output frame counts and every JSONL timestamp checked. Counts are observations,
  not identities or violations. No ground truth or accuracy measured.
- Reviewed frame references: building 0 and 50, street 75. Missed person boxes and
  suspected false helmet boxes motivate the untested hypotheses in BASELINE_CPU.md.
- Repeat building run: detection JSONL byte-identical, SHA-256
  `b973ca43de30a28e6422c7a6610d14ce9c10c26a541b649968d951ecae7e1a85`;
  timing varied to 2.538 FPS. A compatibility smoke ran during part of the repeat;
  repeat timing is not a fair performance comparison.
- Human annotations and quantitative reference evaluation remain pending.

## TRACK-001 — person-only baseline and diagnostics (reported 2026-10-11)

- Pinned source inspected for adapter signature, returned box layout, empty-frame
  updates, score bands, process-global IDs and direct frame buffer semantics.
- Added lap 0.5.12 explicitly; baseline image lacked it. Auto-install disabled.
- Four baseline replays: both trackers, both clips, byte-identical detector inputs.
- Predeclared T1/T2/T3 in TRACKING_EXPERIMENT_PLAN.md; all executed and retained.
- T1: conf 0.10 fresh detection runs, both trackers. Street no-person frames 92→69;
  no-track frames ByteTrack 112→97, BoT-SORT 104→97. No recall/precision truth.
- T2: BoT-SORT street GMC off: IDs 9→12, no-track frames 104→112, gaps 20→11.
  Fewer gaps alongside fewer observations is not an improvement claim.
- T3: building buffer 30→5: IDs 3→4; original ID 1 gap 52→69 replaced by new ID 12
  by frame 75 in short-buffer output. No manually scored identity switch.
- Both street baseline repeats produce byte-identical JSONL; timings vary notably
  with host workload. Evidence export overlapped portions of later runs.
- All 12 annotated videos  / 1,824 records validated for counts, timestamp alignment
  and hashes. RSS approximately 276–281MiB, sampling includes loaded libraries.
- Provisional visual duplicate-worker case: street 125, BoT-SORT IDs 32/33; detector
  already supplied overlapping boxes. No automatic deduplication applied.
- Exported 298 raw frames, original-model overlays, manifests and empty reference
  templates. Fixed number-input change-event issue and verified browser navigation.
- Docker Desktop was stopped when a resumed validation call attempted to connect;
  started it normally and reran the expanded suite.17 tests passed on Windows and
  Linux Docker. Lightweight environment 54 pass, vision integration intentionally skips.
- No human labels, formal tracking accuracy, safety events, GPU or training results.
  Details and exact configs: TRACKING_COMPARISON.md and TRACKING_REPRODUCTION.md.

## ANNOTATION-001 — person reference workflow (2026-10-12)

- PR #1 merged with user approval; main synchronized to e1eefd9. Annotation work
  isolated on feat/reference-annotation-workflow.
- Added manual person boxes and identities, copy-forward without review, coordinate
  correction, exclusion notes, selected contiguous intervals, JSON save/import and
  browser draft caching. Model overlays remain hidden initially.
- Version 2 documents bind to source manifest/video/dimensions/frame count. Explicit
  no-person confirmation is required for reviewed empty frames. Edits invalidate
  review/attestation. Nonhuman drafts cannot claim human attestation.
- Added validate-reference and freeze-reference commands. Freeze verifies source
  JPEG hashes, retains exact submitted JSON bytes and refuses output overwrites.
  It records a reviewer declaration, not independently audited label quality.
- Exported both real clips to data/annotation/ (298 frames). Browser test exercised
  drawing, unresolved-ID rejection, identity assignment, copy-forward, invalid box
  rejection, download, undo, reopen and wrong-clip rejection. Downloaded software
  fixture validated in Python and was correctly refused by freeze. Reset draft.
- 79 local foundation tests pass, seven Node tests pass, Ruff passes. Lightweight
  environment skips vision integration; dedicated existing CI job retained.
- Human labels, accuracy metrics, held-out scene, PPE events and training still pending.

## EVAL-001 — frozen person-reference evaluator (2026-10-12)

- Built on the annotation branch without merging PR #2. Separate branch:
  feat/person-reference-evaluation.
- Added strict frozen-reference loading, source/video/image binding, full-stream
  checksum validation and an explicit fixed-threshold matching/ignore protocol.
- Both tracker inputs must use identical detector JSONL and baseline-summary bytes.
  Default detector IoU/confidence 0.5/0.25; ignore prediction-IoA 0.5. All emitted
  tracks are evaluated; clipped zero-area estimates remain false-positive candidates.
- Detection assignment maximizes valid pair count before summed IoU. Tracking uses
  motmetrics 1.4.0 with SciPy: continuity-preserving CLEAR association and global IDF1.
  Reports interval counts, precision/recall/F1, IDF1, MOTA, MOTP, switches and fragments,
  plus per-frame misses/false positives/switch diagnostics. No mAP/HOTA implementation.
- Installed a separate pinned numerical environment. Exact hand-calculated software
  examples, source corruption, empty intervals, geometry, ignore interaction, selected
  intervals, repeatability and output protection are tested. These are not human labels.
- The new parser accepted eight real baseline/confidence-variant tracking streams;
  no accuracy was calculated. Existing unreviewed references remain unchanged.
- Additional upstream test attempt found removed pandas assertion/merge APIs and a
  missing optional benchmark plugin. Non-benchmark metric tests pass; the unused
  legacy multi-sequence merge helper remains outside the supported runner scope.
- Human label QA/freezing and a separate held-out scene remain research prerequisites.
  No new inference, human annotation, training or safety reliability claim.
- Publication verification (2026-10-13): 138 repository tests pass in the evaluation
  environment, 103 in the lightweight environment (overlapping suites), seven Node
  tests and 14 upstream non-benchmark metric tests pass. Ruff, dependency checks
  and wheel build pass. Actual unreviewed building template rejected with no result.
