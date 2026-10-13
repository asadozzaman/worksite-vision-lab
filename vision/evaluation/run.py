"""Source-bound person evaluation against an explicitly reviewed frozen interval."""

import csv
import hashlib
import json
import platform
import tempfile
from contextlib import ExitStack, closing
from pathlib import Path

from vision.evaluation.config import EvaluationConfig
from vision.evaluation.geometry import clip_box
from vision.evaluation.metrics import DetectionMetrics, TrackingMetrics, evaluation_runtime
from vision.evaluation.reference import load_frozen_reference
from vision.evaluation.sources import (
    DetectionFrame,
    FrameStream,
    TrackFrame,
    bind_baseline,
    bind_tracker,
    output_digest,
    read_summary,
    validate_detections,
    validate_tracks,
)
from vision.provenance import sha256_file


def _report(summary):
    def display(value):
        return (
            "undefined" if value is None else f"{value:.6f}" if isinstance(value, float) else value
        )

    lines = [
        "# Person evaluation on reviewed reference interval",
        "",
        f"Split: {summary['split']}. Frames: {summary['review_interval']}. "
        f"Evaluated frames: {summary['evaluated_frames']}.",
        "",
        "These scores describe this reviewed subset under the declared custom protocol. "
        "Human attestation is a declaration; independent annotation QA is still required.",
        "",
        "| Output | TP | FP | FN | Precision | Recall | F1 | IDF1 | MOTA | Switches | Fragments |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in {"person_detector": summary["detection"], **summary["tracking"]}.items():
        cells = [
            name,
            *(
                values.get(k)
                for k in (
                    "true_positives",
                    "false_positives",
                    "false_negatives",
                    "precision",
                    "recall",
                    "f1",
                    "idf1",
                    "mota",
                    "num_switches",
                    "num_fragmentations",
                )
            ),
        ]
        lines.append("| " + " | ".join(str(display(v)) for v in cells) + " |")
    lines += [
        "",
        "Detection matching maximizes eligible one-to-one pair count, then summed IoU. "
        "Tracking uses motmetrics continuity-preserving CLEAR assignment and global identity "
        "matching. Different assignment rules can produce different localization counts.",
        "",
        "MOTP is mean IoU distance (lower is better); mean_matched_iou is 1 − MOTP. "
        "MOTA may be negative. Undefined ratios are null in JSON and blank in CSV. "
        "Detection IDF1/MOTA columns are not applicable.",
        "",
        "This output does not compute mAP, HOTA, PPE accuracy, unique-worker counts, "
        "safety-event reliability or a ranking on unseen scenes.",
        "",
        "Policy, denominators, dependencies and source/code hashes are in comparison.json. "
        "Frame-linked assignments, misses, false positives and switches are in frames.jsonl.",
    ]
    return "\n".join(lines) + "\n"


def _csv(path, summary):
    fields = [
        "output",
        "true_positives",
        "false_positives",
        "false_negatives",
        "precision",
        "recall",
        "f1",
        "idf1",
        "mota",
        "num_switches",
        "num_fragmentations",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for name, result in {
            "person_detector": summary["detection"],
            **summary["tracking"],
        }.items():
            writer.writerow({"output": name, **result})


def evaluate_person(
    reference_folder, images, video, baseline_folder, tracking_folders, config_path, output
):
    """No named result directory is published until all streams and hashes validate."""
    if output.exists():
        raise FileExistsError(f"evaluation output already exists: {output}")
    reference, manifest, frozen_hashes = load_frozen_reference(reference_folder, images)
    if sha256_file(video) != reference.video_sha256:
        raise ValueError("evaluation video differs from reference")
    config_bytes = config_path.read_bytes()
    config = EvaluationConfig.model_validate_json(config_bytes)
    baseline, baseline_digest = read_summary(baseline_folder)
    person_class, names = bind_baseline(baseline, reference, config)
    if len(tracking_folders) != 2:
        raise ValueError("provide one ByteTrack and one BoT-SORT run")
    trackers, streams = {}, {}
    for folder in tracking_folders:
        summary, digest = read_summary(folder)
        kind = bind_tracker(summary, baseline, baseline_digest, person_class, reference)
        if kind in trackers:
            raise ValueError("comparison requires one ByteTrack and one BoT-SORT run")
        trackers[kind] = {
            "run": folder.name,
            "summary_sha256": digest,
            "configuration": summary["tracker"],
        }
        streams[kind] = FrameStream(
            folder / "tracks.jsonl",
            TrackFrame,
            output_digest(summary, "tracks.jsonl"),
            reference,
        )
    runtime = evaluation_runtime()
    runtime["python"] = platform.python_version()
    detection_stream = FrameStream(
        baseline_folder / "detections.jsonl",
        DetectionFrame,
        output_digest(baseline, "detections.jsonl"),
        reference,
    )
    detector = DetectionMetrics(config)
    ids = [identity.person_id for identity in reference.identities]
    metrics = {kind: TrackingMetrics(config, ids) for kind in sorted(trackers)}
    ordered = sorted(trackers)
    filtered = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".worksite-eval-", dir=output.parent) as temporary:
        stage = Path(temporary)
        with ExitStack() as stack:
            # Close generators even when another stream fails; important for Windows file handles.
            iterators = [
                stack.enter_context(closing(iter(s)))
                for s in (detection_stream, *(streams[k] for k in ordered))
            ]
            evidence = stack.enter_context(
                (stage / "frames.jsonl").open("w", encoding="utf-8", newline="\n")
            )
            for records in zip(*iterators, strict=True):
                detection_frame, *track_frames = records
                validate_detections(detection_frame, names, baseline["parameters"]["conf"])
                for track_frame in track_frames:
                    validate_tracks(track_frame, detection_frame, person_class)
                index = detection_frame.frame_index
                if not reference.review_start <= index <= reference.review_end:
                    continue
                person_predictions = []
                for i, prediction in enumerate(detection_frame.detections):
                    if prediction.class_id != person_class:
                        continue
                    if prediction.confidence < config.min_detection_confidence:
                        filtered += 1
                        continue
                    person_predictions.append({"index": i, "xyxy": prediction.xyxy})
                detail = {
                    "frame_index": index,
                    "timestamp_seconds": index / reference.fps,
                    "detection": detector.update(reference.frames[index], person_predictions),
                    "tracking": {},
                }
                for kind, frame in zip(ordered, track_frames, strict=True):
                    predictions = [
                        {
                            "index": i,
                            "track_id": t.track_id,
                            "xyxy": clip_box(t.xyxy, reference.width, reference.height),
                        }
                        for i, t in enumerate(frame.tracks)
                    ]
                    detail["tracking"][kind] = metrics[kind].update(
                        reference.frames[index], predictions
                    )
                evidence.write(json.dumps(detail, allow_nan=False) + "\n")
        selected = reference.frames[reference.review_start : reference.review_end + 1]
        summary = {
            "schema_version": 1,
            "status": "completed",
            "scope": "person_tracking",
            "split": reference.split,
            "review_interval": [reference.review_start, reference.review_end],
            "evaluated_frames": len(selected),
            "full_video_frames_validated": reference.frame_count,
            "reviewer": reference.reviewer,
            "annotation_version": reference.annotation_version,
            "human_attested": True,
            "reference_quality_independently_verified": False,
            "reference_boxes": sum(len(f.people) for f in selected),
            "ignored_reference_boxes": sum(b.ignore for f in selected for b in f.people),
            "reference_identities_in_interval": len(
                {b.person_id for f in selected for b in f.people if not b.ignore}
            ),
            "sources": {
                **frozen_hashes,
                "video_sha256": reference.video_sha256,
                "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                "detector": {
                    "run": baseline_folder.name,
                    "summary_sha256": baseline_digest,
                    "detections_sha256": detection_stream.digest,
                    "parameters": baseline["parameters"],
                    "model": baseline["model"],
                },
                "trackers": {
                    k: {**trackers[k], "tracks_sha256": streams[k].digest} for k in ordered
                },
                "annotation_manifest_predictions": {
                    k: manifest.get(k) for k in ("detections_sha256", "tracking_sha256")
                },
            },
            "policy": config.policy(),
            "runtime": runtime,
            "code_sha256": {p.name: sha256_file(p) for p in Path(__file__).parent.glob("*.py")},
            "detection": {**detector.summary(), "confidence_filtered_predictions": filtered},
            "tracking": {k: metrics[k].summary() for k in ordered},
            "computed_metrics": [
                "person_precision_recall_f1",
                "IDF1",
                "MOTA",
                "MOTP",
                "CLEAR_switches",
                "CLEAR_fragmentations",
            ],
            "limitations": [
                "scores describe the selected reviewed interval only",
                "human declaration and hashes do not independently certify label quality",
                "custom preprocessing; not official MOTChallenge benchmark results",
                "mAP, HOTA, PPE and event metrics are not computed",
                "final test-set reuse and tuning must be documented externally",
            ],
        }
        (stage / "report.md").write_text(_report(summary), encoding="utf-8")
        _csv(stage / "metrics.csv", summary)
        summary["output_hashes"] = {
            name: sha256_file(stage / name) for name in ("frames.jsonl", "report.md", "metrics.csv")
        }
        (stage / "comparison.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        # Atomic reservation refuses an existing directory on Windows and Linux.
        # Publish comparison.json last, so interrupted publication has no completed summary.
        output.mkdir(exist_ok=False)
        for name in ("frames.jsonl", "report.md", "metrics.csv", "comparison.json"):
            (stage / name).replace(output / name)
    return summary
