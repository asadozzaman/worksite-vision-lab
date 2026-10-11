# CPU detection baseline — 2026-10-10

**Real inference executed on two licensed construction/worksite videos.**
This is a qualitative baseline, not a benchmark accuracy result. No training,
tracking, PPE association or safety-event logic was applied.

## Fixed settings and measured outputs

SiteGuard YOLO26n PPE, SHA-256
`b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`;
Ultralytics 8.4.173, Torch 2.7.0+cpu, Python 3.11.17, OpenCV 4.11.0.
Docker Desktop/WSL2 on the Windows laptop, CPU limit 2, memory 2 GiB,
Torch/OpenCV threads 2. Other host applications were running; this is not an
isolated hardware benchmark. No CUDA execution.

Normalized inputs: 360×640, 25 fps; inference `imgsz=640`, confidence 0.25,
IoU 0.7, max detections 300, seed 0. End-to-end one-to-one head restored explicitly
to the producer version's behavior; IoU is recorded but no conventional NMS is
applied in this mode. No parameter tuning between the two baseline runs.

| Run | Frames | Processing seconds | Processing FPS | Person box observations |
|---|---:|---:|---:|---:|
| Building site, Akum20 (CC0) | 131 | 56.690 | 2.311 | 205 |
| Street works, KabanDanish (CC BY 4.0) | 167 | 53.625 | 3.114 | 166 |

Processing includes decoding, prediction, drawing and saving, excludes model load
and one synthetic warmup. These are single-run observations on a constrained
container, not native CPU throughput estimates. Counts are repeated box observations,
not unique people. Detailed settings, hashes, class counts and timing components
are in `experiments/results/*-baseline.json`.

Both output videos were decoded/count-checked with ffprobe. Their frame counts
match all 298 JSONL records, whose indexes and timestamps were verified. The first
clip was run again using the same normalized bytes/settings; see
`building-repeat-check.json` for exact detection-record comparison. This verifies
repeatability on this environment, not portability across all hardware.

## Frame-linked qualitative review

Reviewer: assistant visual inspection. These are provisional findings for human
review, **not independently human-labeled ground truth**. Source and output frames
are available locally; no external images or videos are committed to Git.

| Reference | Expected visual behavior | Observed output | Category / next investigation |
|---|---|---|---|
| Building frame 0, 0.000 s | Foreground worker should have a person box; visible head should not automatically imply helmet | Cropped right worker gets Person 0.799; foreground worker lacks Person; helmet 0.317 overlaps head | Missed person / suspected false helmet; review original-resolution head and body labels |
| Building frame 50, 2.000 s | Visible foreground worker and cropped right worker should be considered separately | Foreground gets Person ~0.71 and helmet ~0.44; cropped right worker lacks a person box | Truncation sensitivity and suspected helmet false positive; freeze reviewer labels before threshold/resolution tests |
| Street frame 75, 3.000 s | Several visible people should be considered for person detection, including occlusion flags | Output contains a vest box ~0.34 and no person boxes in this inspected frame | Missed people under blur/zoom/partial occlusion; compare person fallback on identical input |

The class `none` appears frequently (184 building observations), but its semantics
remain unresolved. It is not relabeled as missing vest. Gear predictions are not
associated to workers, and absent detections do not become violations.

## Planned controlled hypotheses — not executed

1. A verified official person detector may improve worker recall on the same frames
   compared with the PPE checkpoint's Person class. Requires frozen person boxes.
2. Lower confidence may recover missed people while increasing false positives.
   Compare 0.10 versus 0.25 on the same input, with a predeclared recall/precision criterion.
3. Preserving more source resolution may improve distant-worker recall at a speed
   cost. Compare a new higher-resolution derivative, explicitly treating resolution
   as the experimental variable rather than mixing it into the baseline.

No success claim is made for these hypotheses. The reference subset needs a human
reviewer before quantitative tuning. Neither clip is long/diverse enough to support
general claims about construction safety. Training is not justified by this small
baseline alone.

## Artifacts and next gate

Reproduction: [BASELINE_REPRODUCTION.md](../../docs/BASELINE_REPRODUCTION.md).
Locally, `data/runs/building-baseline/` and `data/runs/street-baseline/` hold annotated
videos, sampled evidence frames and JSONL. Share the street derivative only with
KabanDanish/source/CC BY 4.0 attribution and modification notice. No worker identity,
endorsement or real-world violation claim is attached.

Phase 1 inference is demonstrated. Human reference annotation and independent
accuracy evaluation are pending. Next: freeze reviewed worker annotations, then
compare ByteTrack and BoT-SORT on identical person-only detections. Worker detector
misses must be separated from tracker failures.
