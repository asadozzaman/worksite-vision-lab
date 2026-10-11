# Tracking observations: pre-execution plan

2026-10-10. Written after the first baseline tracking runs and before the changes
below are run. Both short source clips are **development** footage. There is no
held-out final test set or human identity annotation yet. All criteria below are
observational diagnostics, not accuracy acceptance criteria or model selection.
Do not promote a configuration as better on these proxies alone.

Fixed: checkpoint SHA `b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`,
normalized clip bytes from baseline manifests, 25 fps, 360×640, model imgsz640,
Ultralytics8.4.173, two CPU threads and two-CPU/2 GiB container limit. Record timing
separately for inference and cached tracking. Run sequentially; no paid compute.

| Experiment | Observed motivation and hypothesis | Single changed variable | Predeclared observable | Budget |
|---|---|---|---|---|
| T1 | Street baseline has many frames without people/track output. Retaining weaker detections may permit second-pass matches. | Detection conf 0.25 → 0.10; same tracker configs | Fewer frames without person detections and tracks; inspect new boxes for plausible false positives. No recall claim without labels. | One new detector run per clip; both trackers replay each output |
| T2 | Handheld street clip shows strong viewpoint/scale motion. GMC may help association, but sparse flow may be unreliable under blur. | BoT-SORT sparseOptFlow → none on street, original detections | Compare emitted IDs, output gaps, no-track frames and update time. Human identity labels required to decide correctness. | One replay |
| T3 | Building track 1 has a 16-frame gap and later reappears with same ID. Reducing buffer may end this continuity. | ByteTrack track_buffer 30 → 5 on building, original detections | More emitted IDs or altered gap links; inspect interval 52–69. More IDs alone does not establish fragmentation. | One replay |

Also repeat the two baseline tracker algorithms on the street clip to compare
records byte-for-byte. Timing remains a single-host observation with other host
applications running. Record all results including null or contrary findings.

Source: [version-pinned BYTETracker implementation](https://github.com/ultralytics/ultralytics/blob/v8.4.173/ultralytics/trackers/byte_tracker.py),
[BoT-SORT implementation](https://github.com/ultralytics/ultralytics/blob/v8.4.173/ultralytics/trackers/bot_sort.py).
The pinned version uses buffer directly in frames (30 = 1.2s at25fps); do not
assume older API's frame-rate scaling. ReID is explicitly off.
