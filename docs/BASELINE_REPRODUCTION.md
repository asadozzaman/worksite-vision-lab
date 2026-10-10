# Reproduce the real-video CPU baseline

The two executed runs use the checksum-pinned SiteGuard checkpoint under its
embedded AGPL declaration, with no redistribution of weights. See
[model research](MODEL_RESEARCH.md) for isolated loading and rights limitations.

## Acquire the inputs

Download the original files linked on:

- [Men at work in building site](https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm)
  by Akum20, CC0. Save `data/videos/commons-building-site.webm`.
- [Manual workers 2026](https://commons.wikimedia.org/wiki/File:Manual_workers_2026.webm)
  by KabanDanish, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Save `data/videos/commons-manual-workers.webm`. Any shared derivative must credit
  author/source/license and describe resizing, resampling, removed audio and overlays.

Verify the original SHA-256 values in `docs/assets.json`. Obtain the model using
the commit-pinned command in MODEL_RESEARCH.md. All binary inputs stay outside Git.

## Normalize once, then reuse

From the installed foundation environment with FFmpeg on PATH:

```powershell
.\.venv\Scripts\python.exe scripts/normalize_video.py data/videos/commons-building-site.webm data/normalized/building.mp4
.\.venv\Scripts\python.exe scripts/normalize_video.py data/videos/commons-manual-workers.webm data/normalized/street.mp4
```

The script preserves originals and creates 360×640, 25 fps H.264 inputs, without
audio, plus a JSON manifest with source/output hashes, command, FFmpeg version and
decoded frame count. It refuses existing outputs. The street source's audio header
warning is recorded; the video stream decoded successfully. Different FFmpeg builds
may yield different encoded hashes; all compared experiments must reuse the exact
same normalized files and manifest.

## Run isolated inference

Build the image per MODEL_RESEARCH.md, then:

```powershell
./scripts/run_baseline.ps1 -Video building -RunName building-baseline
./scripts/run_baseline.ps1 -Video street -RunName street-baseline
```

Outputs go under `data/runs/<RunName>/`: `annotated.mp4`, `detections.jsonl`,
`summary.json`, and sampled annotated JPG frames. Existing run directories are
rejected. Failures leave `failure.json` instead of a completed summary.

The wrapper mounts code/model/inputs read-only and only the output directory
writable; network is disabled, user is non-root, memory is capped at 2 GiB and
CPU at two cores. No user credentials or home directory are mounted.

The reusable CLI is `python -m vision.detection.run --help`. It accepts model,
video, normalization manifest, output, device, resolution, confidence, IoU and
thread count. `--device cuda:0` is supported by the adapter but **not executed**;
the provided container has CPU-only Torch. A GPU run needs a separately verified
CUDA environment and must be reported independently.

Linux users can run the same module in Docker with the equivalent bind mounts
shown in the PowerShell wrapper. The exact observed Linux Python package set is
in `requirements/vision-linux-observed.lock.txt`; base and built image identities
are recorded. The Dockerfile pins primary dependencies but not all OS packages;
it is not claimed to be a bit-for-bit reproducible image build.

## Interpret outputs correctly

Coordinates refer to the normalized 360×640 input. Frames start at zero;
timestamps are `frame_index / 25`. Empty frames are included. Detection counts
are box observations across frames, **not unique workers or violations**.
Timing excludes load and one synthetic warmup, and includes decoding, prediction,
drawing and writing. A single run is an observation, not a hardware benchmark.
No ground truth, precision/recall/mAP, identity score or event accuracy is present.

See [baseline report](../experiments/reports/BASELINE_CPU.md) for observed failures.
