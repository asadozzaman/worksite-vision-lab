# Engineering readiness

Reviewed 2026-10-13. This document distinguishes demonstrated engineering from
remaining research and application work. It records current capabilities and
the acceptance gates that remain open.

## Evidence a reviewer can inspect

| Area | Demonstrated | Limit |
|---|---|---|
| Reproducibility | Pinned runtime settings, source/output hashes, saved detector streams and repeat comparisons | FFmpeg/OS builds and host workload can change encoded bytes and timings |
| Model verification | Checksum-pinned restricted load in an offline container; strict official architecture match and actual class metadata | Training lineage and data rights are not independently audited |
| Experiment design | Identical detector input for tracker comparisons; three declared diagnostic variables; contrary results retained | Two short development clips; no independent test scene |
| Data integrity | Full-stream indexes/timestamps, source bindings, bounded evaluation records and output overwrite protection | Hashes establish byte identity, not label correctness |
| Reference workflow | Independent manual IDs, uncertainty/exclusion notes, explicit empty-frame review and human freeze gate | Draft labels still need correction and independent QA |
| Metrics | Hand-calculated software cases, pinned CLEAR/Identity implementation and declared denominators | No real-video scores yet; no mAP/HOTA/PPE/event metrics |
| Maintainability | Separate detection, tracking and evaluation modules; Windows/Linux Python and Node CI | No packaged end-to-end application or clean-machine release demonstration yet |
| Demonstration | Actual frame-aligned detector/tracker figure and structured research records | No interactive public application, stable hardware benchmark or event demo |

Local and CI validation details are recorded in [phase status](PHASE_STATUS.md).
For current GitHub checks, use the commit/PR-specific Actions results; an earlier
passing run does not establish that a newer commit passed.

## Remaining acceptance gates

1. Correct and review all selected person frames, check identity continuity and
   exclusions independently, then freeze an annotation version. Draft geometry and
   tracker output cannot supply the reference truth.
2. Run baseline person evaluation on that reference and publish denominators,
   matching settings, failures and exact input hashes. Compare controlled variants
   on development data without promoting output coverage to accuracy.
3. Acquire a distinct source/camera scene and reserve it before tuning. Add longer
   sequences with entry/exit, overlap and occlusion; document licensing and labels.
4. Measure PPE association and temporal event behavior against reviewed PPE/event
   intervals, preserving unknown states. Evaluate false alarms, misses and latency.
5. Build and test the real upload-to-result API/dashboard flow, including failures,
   file isolation, bounded uploads and responsive evidence inspection.
6. Reproduce the CPU demonstration from a clean checkout, record environment and
   resource measurements, and complete release validation.

These gates define the evidence needed for a strong engineering portfolio. Visual
polish and passing software tests cannot substitute for measured CV performance.

## Repository presentation

Active branches use descriptive `feat/` names and commits describe concrete changes.
Historical PR records are retained. Review provenance is deliberately explicit: draft preparation,
software fixtures and completed human review are different evidence states.
Removing that distinction would weaken the evaluation rather than improve it.
