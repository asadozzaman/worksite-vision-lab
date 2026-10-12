# Reproduce tracking and evidence review

Run from the repository root after completing [baseline reproduction](BASELINE_REPRODUCTION.md).
The two baseline run folders must contain their original summary and detection
JSONL. Use a new output name for each run; existing results are never overwritten.
All commands below were exercised locally, except the expanded CI job whose
actual status is shown in the PR checks.

## Runtime

```powershell
docker build -f docker/checkpoint-inspector.Dockerfile -t worksite-checkpoint-inspector:8.4.173 .
docker build -f docker/tracking.Dockerfile -t worksite-tracking:8.4.173 .
```

The first image can be reused from baseline work. The tracking layer adds pinned
lap 0.5.12, Pydantic 2.13.4 and pytest 9.0.3. Observed complete package versions are
recorded separately; the image is not claimed to be bit-reproducible across future
APT/package-index changes. Inference and tracking run offline with a read-only
root filesystem, no capabilities, non-root UID, 2 CPUs and 2GiB RAM.

## Fixed-detection comparison

```powershell
./scripts/run_tracking.ps1 -Video building -Tracker bytetrack -RunName building-bytetrack
./scripts/run_tracking.ps1 -Video building -Tracker botsort -RunName building-botsort
./scripts/run_tracking.ps1 -Video street -Tracker bytetrack -RunName street-bytetrack
./scripts/run_tracking.ps1 -Video street -Tracker botsort -RunName street-botsort
```

Outputs: `data/tracking/<run>/tracks.jsonl`, `annotated.mp4`, sample frames and
`summary.json`. Records include every frame, raw Kalman xyxy boxes, original
detection indexes, confidence and video-local ID. Estimates may extend beyond
image boundaries; OpenCV clips their drawing. IDs need not be consecutive because
unconfirmed upstream candidates can consume IDs. Never label their count as
unique people. Lost tracks without current detections are not emitted as observed
people; empty updates still advance tracker age and camera motion state.

`python -m vision.tracking.run --help` exposes the portable path-based CLI.
It requires the vision dependencies, but no checkpoint load. For safe parallel
video processing, use one process per video because upstream ID allocation is
process-global. ReID is intentionally unsupported in the current configuration.

## Diagnostic variants

```powershell
./scripts/run_baseline.ps1 -Video building -RunName building-conf010 -Confidence 0.10
./scripts/run_baseline.ps1 -Video street -RunName street-conf010 -Confidence 0.10
./scripts/run_tracking.ps1 -Video building -Tracker bytetrack -BaselineRun building-conf010 -RunName building-bytetrack-conf010
./scripts/run_tracking.ps1 -Video building -Tracker botsort -BaselineRun building-conf010 -RunName building-botsort-conf010
./scripts/run_tracking.ps1 -Video street -Tracker bytetrack -BaselineRun street-conf010 -RunName street-bytetrack-conf010
./scripts/run_tracking.ps1 -Video street -Tracker botsort -BaselineRun street-conf010 -RunName street-botsort-conf010
./scripts/run_tracking.ps1 -Video street -Tracker botsort -ConfigName botsort-no-gmc -RunName street-botsort-no-gmc
./scripts/run_tracking.ps1 -Video building -Tracker bytetrack -ConfigName bytetrack-short-buffer -RunName building-bytetrack-short-buffer
./scripts/run_tracking.ps1 -Video street -Tracker bytetrack -RunName street-bytetrack-repeat
./scripts/run_tracking.ps1 -Video street -Tracker botsort -RunName street-botsort-repeat
```

`ConfigName` identifies the complete config; its `tracker_type` is authoritative.
`Tracker` supplies the default config name only. Each output summary records the
actual tracker/config. These diagnostic runs do not select a best threshold or
establish accuracy; see [comparison report](../experiments/reports/TRACKING_COMPARISON.md).

## Frame-exact review bundle

Use a Python environment with project+vision dependencies, or mount the same
inputs and exporter into the tracking container. No model is loaded by export.

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/export_review.py --video data/normalized/building.mp4 --baseline data/runs/building-baseline --tracking data/tracking/building-bytetrack data/tracking/building-botsort --output data/review/building --title "Building site: tracking review" --attribution "Men at work in building site - Akum20, CC0. https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm. Modified: resized, resampled, frame extraction and overlays."
python scripts/export_review.py --video data/normalized/street.mp4 --baseline data/runs/street-baseline --tracking data/tracking/street-bytetrack data/tracking/street-botsort --output data/review/street --title "Street works: tracking review" --attribution "Manual workers 2026 - KabanDanish, CC BY 4.0 https://creativecommons.org/licenses/by/4.0/. https://commons.wikimedia.org/wiki/File:Manual_workers_2026.webm. Modified: resized, resampled, frame extraction and overlays."
python -m http.server 8768 --bind 127.0.0.1 --directory data/review
```

Open `http://127.0.0.1:8768/building/` or `/street/`. The exported `index.html` also
works offline with its adjacent image directory. Only the review directory is
served on localhost. New exports include a local person annotation editor with
box drawing, manual identities, per-frame review and JSON save/reopen. It shows raw
frames first, supports exact frame entry, previous/next/arrows, and switches between
detector/tracker overlays. The planned React application remains a later phase.
Keep source attribution when sharing any derivative.

The manifest freezes all raw-frame image hashes, input video hash and record hashes.
The reference template is intentionally empty, `reviewed:false`, `complete:false`.
Do not treat empty labels as confirmed negatives. Follow [the editor workflow](ANNOTATION_WORKFLOW.md)
to validate/freeze labels and [the protocol](ANNOTATION_PROTOCOL.md) before metrics.
If `data/review/` already exists from an earlier export, use `data/annotation/` as
the new output root. Existing version 1 templates are intentionally not migrated
into claimed reviewed labels.

## Verification

```powershell
python scripts/validate_tracking_artifacts.py data/tracking/building-bytetrack data/tracking/street-botsort
python -m pytest tests/test_tracking_integration.py tests/test_tracking_records.py
```

The artifact validator requires ffprobe. Integration tests use explicitly synthetic
software fixtures, never evaluation footage. The lightweight foundation environment
skips vision integration; the dedicated CI job installs the vision dependencies.
Full real-video tests require the separately acquired local assets and are not
silently substituted with synthetic data in CI.
