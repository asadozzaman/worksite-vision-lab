# Person tracking comparison — 2026-10-11

ByteTrack and BoT-SORT ran on both real clips. Twelve replays, two additional
detector runs, three controlled diagnostic changes and two repeatability checks
were executed. **These are observations, not identity accuracy measurements.**
Human identities, detection truth and safety intervals remain unannotated.

## Protocol and provenance

Inputs are the previously normalized building (131 frames) and street (167 frames)
clips, both 360×640 at 25 fps. Each tracker gets identical frozen detector JSONL
and actual decoded frames. Original detector settings/checkpoint hashes are in
every run summary. Only the class resolved as `Person` from model names enters
tracking (index 6 for this checkpoint). PPE boxes retain their original indexes
for future association. A person detection does not determine occupation.

Pinned Ultralytics 8.4.173, lap 0.5.12, Python 3.11.17, NumPy 1.26.4, OpenCV4.11.0,
CPU-only Torch2.7.0. Docker limit: 2 CPUs, 2 GiB; OpenCV/Torch threads2, seed0.
Tracking image: `sha256:14de5c06f736ea1dc28b729d99776dfe0052fa7b69feffa7476b6efbef6fc9d4`.
No model is loaded during replay. The dedicated process keeps one tracker alive
for every frame, including frames with zero detections. Each run starts fresh.
Upstream track IDs use a process-global counter: keep concurrent videos in separate
processes until a per-stream allocation strategy is implemented and tested.

Default high/new threshold0.25, low0.10, buffer30 frames, match0.8, score fusion on.
BoT-SORT uses sparse optical flow for camera motion compensation; ReID is off.
The pinned implementation uses buffer directly in frames:30 frames =1.2s.
The original detector conf0.25 excludes the low-confidence association band;
T1 restores that band without changing tracker thresholds.

Source inspection: [BYTETracker v8.4.173](https://github.com/ultralytics/ultralytics/blob/v8.4.173/ultralytics/trackers/byte_tracker.py),
[BoT-SORT v8.4.173](https://github.com/ultralytics/ultralytics/blob/v8.4.173/ultralytics/trackers/bot_sort.py).

## Baseline observations

| Clip / tracker | Emitted IDs | Track boxes | Frames without tracks | Within-ID gaps | Replay FPS |
|---|---:|---:|---:|---:|---:|
| Building / ByteTrack | 3 | 195 | 0/131 | 8 | 17.329 |
| Building / BoT-SORT | 3 | 196 | 0/131 | 9 | 11.232 |
| Street / ByteTrack | 12 | 83 | 112/167 | 11 | 50.229 |
| Street / BoT-SORT | 9 | 104 | 104/167 | 20 | 27.096 |

Emitted IDs are **not unique real workers**. Gaps are missing observations between
the same output ID, **not fragmentation or ID-switch counts**. An always-present
track on the building clip does not mean every visible worker is tracked.
The detector emits no person boxes on 92/167 street frames, so both trackers
inherit a substantial input limitation.

Replay FPS includes decode/validate/track/render/write, excludes detector inference
and library imports. It is not end-to-end video-analysis FPS. Process RSS sampled
after imports and each frame was approximately276–281MiB. It includes library
memory, is not an exact peak, and excludes the rest of the Docker VM.

Host workload was uncontrolled; evidence export/browser activity overlapped parts
of later runs. ByteTrack street repeat measured23.786 replay FPS versus50.229
initially despite byte-identical records. Do not infer hardware throughput or a
stable speed advantage from these single-run timings.

## Three executed diagnostic experiments

Predeclared variables and observational criteria are in
[TRACKING_EXPERIMENT_PLAN.md](TRACKING_EXPERIMENT_PLAN.md). Both clips are development
data; no final test set was tuned or evaluated. These experiments do not satisfy
the later requirement for labeled reliability comparisons.

**T1 — detection confidence0.25 →0.10.** Fresh real model inference on each same
normalized input; both trackers replay the resulting identical JSONL.

| Clip / tracker | Track boxes, before → after | No-track frames | Within-ID gaps | IDs |
|---|---|---|---|---|
| Building / ByteTrack | 195 →225 | 0 →0 | 8 →1 | 3 →3 |
| Building / BoT-SORT | 196 →227 | 0 →0 | 9 →2 | 3 →3 |
| Street / ByteTrack | 83 →136 | 112 →97 | 11 →6 | 12 →10 |
| Street / BoT-SORT | 104 →137 | 104 →97 | 20 →10 | 9 →9 |

Street frames without person detections fall92 →69. At frame75, the new Person
box has confidence~0.11 and spans a blurred/partially overlapping region. More
boxes and continuity are observable; improved recall, precision or identity
correctness are **not established**. No production threshold is selected.

**T2 — disable BoT-SORT camera motion compensation on street baseline.** Emitted
IDs9 →12, track boxes104 →83, no-track frames104 →112, within-ID gaps20 →11.
Fewer gaps here accompanies fewer output observations; it is not evidence of
better tracking. Sparse flow improves output coverage in this run, but identity
correctness remains unknown. Settings and all outputs are retained.

**T3 — ByteTrack buffer30 →5 on building baseline.** IDs3 →4, track boxes195 →193,
within-ID gaps8 →7. Baseline ID1 is emitted at frames52 and69 with a16-frame gap;
the short-buffer run has no right-side track at69/70 and emits ID12 by75.
This illustrates loss/reacquisition sensitivity, not a scored ground-truth ID switch.

## Frame-linked visual investigations

Reviewer: assistant visual inspection, provisional and not human ground truth.
Machine-readable cases: [failure-cases.json](../results/tracking/failure-cases.json).

- Building50 /2.000s: foreground worker has ByteTrack ID9; cropped right-side
  person has no track. Input has only one person box. Inspect truncation before
  attributing the omission to tracker matching.
- Street75 /3.000s: neither baseline tracker emits a person track despite visible
  people. Baseline has no person box. Lower threshold adds a weak, ambiguous box.
- Street100 /4.000s: BoT-SORT emits IDs19 and33 while other visible people lack
  boxes. IDs represent person candidates, including pedestrians, not verified workers.
- Street125 /5.000s: BoT-SORT IDs32 and33 overlap the same visible high-visibility
  worker. The input contains overlapping person boxes at confidences~0.653 and
  ~0.295. Suspected duplicate tracking is partly rooted in duplicate detections.
  Future controlled person-box deduplication must check crowded-scene suppression
  against human boxes; do not silently alter the frozen baseline.

There is no verified ID-switch count/example labeled by a human, no HOTA/MOTA/IDF1,
no event reliability result and no claim that BoT-SORT is more accurate.

## Validation and next gate

All12 output videos were decoded and frame-count checked with ffprobe; all1,824
JSONL frames were checked for contiguous indexes, exact CFR timestamps, person-only
classes, unique IDs within each frame and artifact hashes. The two street repeats
produce byte-identical tracking records for their respective algorithms. See
`experiments/results/tracking/validation.json` for hashes and measured observations.

The review exporter provides all298 raw normalized frames, optional detector/
tracker overlays, exact frame navigation, source attribution, frozen manifests
and **empty unreviewed** annotation templates. Browser checks covered first/last
frame boundaries, direct frame entry, next-frame alignment and overlay switching.
The original change-only input handler failed to update on programmatic input;
using the input event fixed it and was rechecked.

Next gate: independently review contiguous identities and person boxes, freeze
annotation hashes, and acquire a separate held-out scene before any accuracy-based
tuning. Then evaluate duplicate handling/person-detector fallback and PPE-to-worker
association. Phase2 implementation and proxy comparison work; formal identity
evaluation and Phase3's labeled experiment requirement remain incomplete.

Reproduction: [TRACKING_REPRODUCTION.md](../../docs/TRACKING_REPRODUCTION.md).
