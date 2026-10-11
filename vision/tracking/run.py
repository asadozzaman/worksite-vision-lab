"""Replay a verified detection run through a person-only tracker without model loading."""

import argparse
import json
import math
import platform
import time
from pathlib import Path

from vision.config import resolve_person_class
from vision.detection.run import file_hash
from vision.tracking.config import TrackerConfig
from vision.tracking.records import TrackObservations, validate_frame


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--detections", type=Path, required=True)
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    config = TrackerConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline_summary.read_text(encoding="utf-8"))
    if baseline["status"] != "completed":
        raise ValueError("requires a completed detection run")
    video_hash = file_hash(args.video)
    detection_hash = file_hash(args.detections)
    if baseline["video_sha256"] != video_hash:
        raise ValueError("video checksum mismatch")
    if baseline["output_hashes"]["detections.jsonl"] != detection_hash:
        raise ValueError("detection checksum mismatch")
    names = {int(k): v for k, v in baseline["model"]["names"].items()}
    person_class = resolve_person_class(names)
    width, height, fps = baseline["width"], baseline["height"], baseline["fps"]
    if not math.isfinite(fps) or fps <= 0 or baseline["frame_count"] <= 0:
        raise ValueError("invalid baseline frame count or fps")

    import cv2
    import numpy as np
    import psutil
    import torch
    import ultralytics

    from vision.tracking.adapter import PersonTracker

    torch.set_num_threads(2)
    cv2.setNumThreads(2)
    np.random.seed(0)
    torch.manual_seed(0)
    tracker = PersonTracker(config, person_class, width, height)
    capture = cv2.VideoCapture(str(args.video))
    writer = None
    created = False
    try:
        if not capture.isOpened():
            raise ValueError("cannot open video")
        actual = (
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        if actual != (width, height) or abs(capture.get(cv2.CAP_PROP_FPS) - fps) > 1e-5:
            raise ValueError("video metadata mismatch")
        args.output.mkdir(parents=True, exist_ok=False)
        created = True
        writer = cv2.VideoWriter(
            str(args.output / "annotated.mp4"),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            raise RuntimeError("MP4 writer unavailable")
        observations = TrackObservations()
        frame_count = 0
        update_seconds = 0.0
        process = psutil.Process()
        peak_sampled_rss = process.memory_info().rss
        started, cpu_started = time.perf_counter(), time.process_time()
        with (
            args.detections.open(encoding="utf-8") as source,
            (args.output / "tracks.jsonl").open("w", encoding="utf-8", newline="\n") as output,
        ):
            for index, line in enumerate(source):
                record = json.loads(line)
                validate_frame(record, index, baseline)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError("video ended before detection records")
                tick = time.perf_counter()
                tracks, people_count = tracker.update(record["detections"], frame)
                update_seconds += time.perf_counter() - tick
                tracked = {
                    "frame_index": index,
                    "timestamp_seconds": index / fps,
                    "width": width,
                    "height": height,
                    "person_detection_count": people_count,
                    "tracks": tracks,
                }
                observations.update(tracked)
                output.write(json.dumps(tracked, allow_nan=False) + "\n")
                for track in tracks:
                    x1, y1, x2, y2 = (int(round(v)) for v in track["xyxy"])
                    color = (80, 220, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        f"ID {track['track_id']} {track['confidence']:.2f}",
                        (max(0, x1), max(16, y1)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        color,
                        1,
                    )
                cv2.putText(
                    frame,
                    f"{config.tracker_type} | {index} | {index / fps:.2f}s",
                    (8, height - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (255, 255, 255),
                    1,
                )
                writer.write(frame)
                if index % 25 == 0:
                    cv2.imwrite(str(args.output / f"frame-{index:06d}.jpg"), frame)
                frame_count += 1
                peak_sampled_rss = max(peak_sampled_rss, process.memory_info().rss)
            if capture.read()[0] or frame_count != baseline["frame_count"]:
                raise ValueError("video and detection frame counts disagree")
        writer.release()
        writer = None
        elapsed, cpu_seconds = time.perf_counter() - started, time.process_time() - cpu_started
        summary = {
            "schema_version": 1,
            "status": "completed",
            "tracker": config.model_dump(),
            "person_class_id": person_class,
            "source_video_sha256": video_hash,
            "source_detections_sha256": detection_hash,
            "source_baseline_summary_sha256": file_hash(args.baseline_summary),
            "source_model": baseline["model"],
            "source_detector_parameters": baseline["parameters"],
            "code_sha256": {p.name: file_hash(p) for p in Path(__file__).parent.glob("*.py")},
            "frame_count": frame_count,
            "fps": fps,
            "width": width,
            "height": height,
            "processing_seconds": elapsed,
            "processing_fps": frame_count / elapsed,
            "tracker_update_seconds": update_seconds,
            "tracker_update_fps": frame_count / update_seconds,
            "process_cpu_seconds": cpu_seconds,
            "peak_sampled_process_rss_bytes": peak_sampled_rss,
            "timing_scope": (
                "replay decode/validate/track/render/write; EXCLUDES model inference and imports"
            ),
            "memory_scope": (
                "process RSS sampled after imports and each frame; includes loaded libraries"
            ),
            "threads": 2,
            "seed": 0,
            "runtime": {
                "ultralytics": ultralytics.__version__,
                "opencv": cv2.__version__,
                "numpy": np.__version__,
                "python": platform.python_version(),
            },
            "low_confidence_pass_available": baseline["parameters"]["conf"]
            < config.track_high_thresh,
            "observations": observations.summary(fps),
            "output_hashes": {
                name: file_hash(args.output / name) for name in ("tracks.jsonl", "annotated.mp4")
            },
        }
        (args.output / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    k: summary[k]
                    for k in ("status", "frame_count", "processing_fps", "observations")
                },
                indent=2,
            )
        )
    except Exception as exc:
        # Do not modify a pre-existing run when mkdir failed.
        if created:
            (args.output / "failure.json").write_text(
                json.dumps({"status": "failed", "error": str(exc)})
            )
        raise
    finally:
        capture.release()
        if writer is not None:
            writer.release()


if __name__ == "__main__":
    main()
