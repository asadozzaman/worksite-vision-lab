"""Stream a normalized constant-frame-rate video through the audited PPE model.

Run inside the documented isolated Docker environment. Output must be a new directory.
"""

import argparse
import hashlib
import json
import math
import platform
import time
from collections import Counter
from pathlib import Path

from vision.detection.records import frame_record


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--normalization", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.7)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args(argv)
    if not (160 <= args.imgsz <= 1920 and args.imgsz % 32 == 0):
        p.error("imgsz must be 160..1920 and divisible by 32")
    if not (0 < args.conf <= 1 and 0 < args.iou <= 1 and 1 <= args.threads <= 16):
        p.error("invalid thresholds or thread count")
    import cv2
    import numpy as np
    import torch

    from vision.detection.model import load_reviewed_model

    norm = json.loads(args.normalization.read_text(encoding="utf-8"))
    video_sha = file_hash(args.video)
    if norm["output_sha256"] != video_sha:
        raise ValueError("video does not match the normalization record")
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise ValueError("cannot open input video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    expected = norm["frame_count"]
    if not (math.isfinite(fps) and fps > 0 and abs(fps - norm["fps"]) < 1e-5):
        capture.release()
        raise ValueError("input fps disagrees with normalization record")
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    np.random.seed(0)
    cv2.setNumThreads(args.threads)
    writer = None
    started = time.perf_counter()
    try:
        detector, model_meta = load_reviewed_model(args.model)
        settings = dict(
            imgsz=args.imgsz,
            conf=args.conf,
            iou=args.iou,
            max_det=300,
            device=args.device,
            verbose=False,
            save=False,
            end2end=model_meta["effective_end2end"],
        )
        detector.predict(np.zeros((height, width, 3), dtype=np.uint8), **settings)
        warmup_seconds = time.perf_counter() - started
        writer = cv2.VideoWriter(
            str(args.output / "annotated.mp4"),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            raise RuntimeError("MP4 writer unavailable")
        counts = Counter()
        inference_seconds = 0.0
        frame_count = 0
        loop_start = time.perf_counter()
        with (args.output / "detections.jsonl").open("w", encoding="utf-8") as output:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if args.device != "cpu":
                    torch.cuda.synchronize()
                tick = time.perf_counter()
                result = detector.predict(frame, **settings)[0]
                if args.device != "cpu":
                    torch.cuda.synchronize()
                inference_seconds += time.perf_counter() - tick
                detections = [
                    (box[:4], float(box[4]), int(box[5]))
                    for box in result.boxes.data.cpu().tolist()
                ]
                record = frame_record(frame_count, fps, detections, detector.names, width, height)
                output.write(json.dumps(record, allow_nan=False) + "\n")
                counts.update(d["class_name"] for d in record["detections"])
                annotated = result.plot()
                cv2.putText(
                    annotated,
                    f"frame {frame_count} | {frame_count / fps:.3f}s",
                    (8, height - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                )
                writer.write(annotated)
                if frame_count % 25 == 0:
                    cv2.imwrite(str(args.output / f"frame-{frame_count:06d}.jpg"), annotated)
                frame_count += 1
        writer.release()
        writer = None
        elapsed = time.perf_counter() - loop_start
        if frame_count != expected or not frame_count:
            raise RuntimeError(f"decoded {frame_count} frames; expected {expected}")
        summary = {
            "status": "completed",
            "schema_version": 1,
            "model": model_meta,
            "video_sha256": video_sha,
            "normalization": norm,
            "parameters": {**settings, "threads": args.threads, "seed": 0},
            "frame_count": frame_count,
            "fps": fps,
            "width": width,
            "height": height,
            "detection_counts_by_class": dict(counts),
            "count_definition": "box observations across frames, not unique people or violations",
            "load_and_synthetic_warmup_seconds": warmup_seconds,
            "processing_seconds": elapsed,
            "processing_fps": frame_count / elapsed,
            "predict_seconds": inference_seconds,
            "predict_fps": frame_count / inference_seconds,
            "timing_scope": "processing includes decode/predict/draw/write; excludes load/warmup",
            "opencv": cv2.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "gpu_executed": args.device != "cpu",
            "accuracy_measured": False,
            "ground_truth": None,
            "output_hashes": {
                name: file_hash(args.output / name)
                for name in ("detections.jsonl", "annotated.mp4")
            },
        }
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    except Exception as exc:
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
