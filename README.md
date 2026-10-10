# Worksite Vision Lab

An open-source research project for construction video detection, worker tracking,
and evidence-based PPE event review. The aim is to measure failures and alert
reliability before building a client-facing video intelligence application.

**Current status: Phase 0 foundation; not a deployed safety-monitoring system.**
No construction-video accuracy, tracking score, or event reliability has been measured.
See [phase status](docs/PHASE_STATUS.md) for execution evidence and blockers.

## Available now

- Validated, versioned experiment settings and asset provenance records.
- Streaming SHA-256 checksums and bounded static PyTorch checkpoint inspection.
- Local video metadata inspection with FFmpeg, without treating metadata as visual review.
- Environment diagnostics, unit tests, and a Windows/Linux CI configuration.
- An isolated checkpoint verification procedure and research acceptance criteria.

The inference pipeline, tracking comparison, safety event engine, API, and React
dashboard are subsequent gated phases. There are no sample business metrics or
fabricated events in this repository.

## Architecture and roadmap

Video ingestion → YOLO26 detections → person-only tracking → PPE association →
temporal event engine → SQLite/FastAPI → React inspection dashboard.

Each component will use explicit frame indexes, timestamps, asset checksums,
versioned configurations, and experiment IDs. Worker IDs are local to a video,
not biometric or cross-video identities. Unobserved PPE remains unknown.

Planned stack: Ultralytics YOLO26, PyTorch, OpenCV, ByteTrack/BoT-SORT,
FastAPI/Pydantic/SQLite, React/TypeScript/Vite. Only the foundation described
above is currently implemented. See [implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Install the foundation

Python 3.10–3.12 is the initial target. Python 3.10 is tested locally on Windows;
the Docker model inspector uses Python 3.11. The vision dependency set uses
NumPy 1.26 and is not targeted at Python 3.13.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements/foundation.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\worksite.exe doctor
.\.venv\Scripts\python.exe -m pytest
```

Linux/macOS: use `python3 -m venv .venv`, then `.venv/bin/python` and
`.venv/bin/worksite` in the equivalent commands. Linux local foundation execution
is reported separately from the CI matrix; configuration is not proof of a pass.

## Reproduce Phase 0

```text
worksite validate-assets docs/assets.json
worksite validate-config experiments/configs/baseline-cpu.json
worksite inspect-checkpoint data/quarantine/yolo26n_ppe.pt
worksite probe-video data/videos/pexels-38885275.mp4
```

The last two commands require separately acquired assets. `probe-video` also
requires `ffprobe` on PATH. There is no implicit network download or unsafe model
load in these commands. See [asset acquisition](docs/ASSET_ACQUISITION.md) and
[checkpoint research](docs/MODEL_RESEARCH.md) for acquisition and isolated testing.

Static inspection returns records such as `sha256`, `size_bytes`, `globals`, and
`load_performed: false`. It does not certify a checkpoint as safe. Measured local
records are stored in [docs/evidence](docs/evidence).

## Research method

Establish real-video detection before tuning. Freeze manually reviewed annotation
subsets before comparing trackers or temporal alert rules. Keep the model, input
frames, device, thresholds, and resolution identical for controlled comparisons.
Separate observations and proxy counts from metrics with ground truth. Never use
tracker IDs as reference identities or missing detections as proof of missing PPE.

Experiments and failed attempts belong in [the experiment log](docs/EXPERIMENT_LOG.md).
No model training is planned until baseline failures justify it. No Kaggle GPU
run has occurred. No original application code or private data from other projects
has been imported.

## Licensing and limitations

Original code is licensed under AGPL-3.0-only; see [LICENSE](LICENSE).
Dependencies and assets have their own terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
The SiteGuard checkpoint is a candidate under investigation, not a redistributed
project asset. Its repository's MIT license alone does not establish the rights
for its weights or training data. Pexels footage is acquired separately, and raw
video, checkpoints, datasets, credentials, and runtime outputs are ignored by Git.

Research evidence states are not safety certification. There are no real-video
demonstrations or benchmark accuracy claims yet. All later acceptance gates remain
open until actually executed and documented.
