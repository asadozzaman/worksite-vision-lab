# Reference annotation protocol

Planned protocol, not completed annotation. No frames or worker identities have
been labeled yet. This document defines the evidence needed for later phases.

## Input freeze and review

Register original and normalized video hashes, exact normalization command,
frame rate, resolution and frame count before annotation. Select clips by camera
and scene, then assign whole clips to development or final test partitions.
Adjacent frames from one scene must not cross partitions. Keep a held-out test
manifest and do not tune against it. Two clips alone are inadequate evidence of
generalization to all construction sites.

Review full playback plus individual frames. Label actual visible content, not
detector predictions or clip titles. For an initial qualitative review, inspect
every 25th normalized frame plus transitions/occlusions. For identity/event metrics,
label contiguous intervals at every evaluated frame; sparse keyframes alone cannot
support a reliable count of identity switches or event latency.

## Reference records

Each record needs video hash, zero-based frame index, timestamp, annotation
version, reviewer and revision history. Boxes use pixel `xyxy` in normalized
input coordinates, with origin at top left. Record image dimensions alongside them.

- Worker: box, manually assigned video-local identity, visible fraction or
  visibility category, occlusion, truncation, and ignore/uncertainty flags.
- PPE: box, class, assigned worker identity when clear, otherwise unassigned;
  include visible, occluded and indeterminate evidence. Do not label unseen PPE
  as absent. Define any explicit missing-PPE class using source annotation guidance.
- Safety interval: rule, worker identity, start/end frame, visible evidence,
  uncertainty and reviewer confidence. Restricted zones require a versioned polygon
  and a documented point-in-zone convention (for example, bottom-center of person box).
- Failure: frame/interval reference, expected and observed behavior, taxonomy,
  suspected cause, evidence path and proposed controlled experiment.

Manually reviewed identities are distinct from tracker IDs. Do not reuse tracker
output IDs as truth. No face recognition or real-world identity collection.

## Metric gates

Detection precision/recall/F1 require one-to-one, class-aware matching with a
declared IoU and confidence threshold, treatment of ignored boxes and complete
annotations for the measured classes. mAP requires a verified implementation,
declared IoU sweep and class inclusion policy. A few reviewed frames support
qualitative failure counts, not a benchmark accuracy claim.

Identity metrics require contiguous, complete worker identity labels and declared
ignore rules. Report formal scores only using a validated implementation. Track
counts, lifespan and gaps are observational proxies, never identity accuracy.

Event metrics require manually reviewed reference intervals and a declared matching
rule, overlap/time tolerance and duplicate-event policy. Separate false alerts per
video-minute, missed intervals, recall, confirmation delay and duplicate counts.
Report denominators and uncertainty; count reviewed false alarms independently from
unreviewed suspected events. Unknown during occlusion does not imply recovery.

## Controlled experiment record

Before execution, record hypothesis, annotation hash, clip partition, fixed model
hash, device, resolution, threshold, tracker config hash, event parameters,
success criterion and run budget. Save the untouched baseline and all candidate
results, including failed attempts. Select on development data; evaluate the frozen
test set once after the method is chosen. Document any later test-set reuse.

Initial detection confidence 0.25 is a baseline setting, not a chosen tracking
optimum. ByteTrack's low-score association needs low-confidence detections retained;
detector filtering can remove them before tracking. In the tracking phase, inspect
installed tracker thresholds, select the shared detector input policy before the
comparison, and apply it identically to both trackers.
