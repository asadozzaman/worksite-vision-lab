"""Render a source-verified building baseline figure without inference or reference labels."""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from vision.evaluation.sources import (
    MAX_LINE_BYTES,
    DetectionFrame,
    FrameStream,
    TrackFrame,
    bind_baseline,
    bind_tracker,
    output_digest,
    validate_detections,
    validate_tracks,
)
from vision.provenance import sha256_file

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "baseline_summary": ROOT / "experiments/results/building-baseline.json",
    "detections": ROOT / "experiments/results/building-baseline.jsonl",
    "tracking_summary": ROOT / "experiments/results/tracking/building-botsort.json",
    "tracks": ROOT / "experiments/results/tracking/building-botsort.jsonl",
}


def read_summary(path):
    if path.stat().st_size > MAX_LINE_BYTES:
        raise ValueError("summary exceeds 8 MiB")
    raw = path.read_bytes()
    doc = json.loads(raw)
    if doc.get("status") != "completed":
        raise ValueError("figure requires completed prediction runs")
    return doc, hashlib.sha256(raw).hexdigest()


def render(video, output, frame_index):
    if output.exists():
        raise FileExistsError("figure output directory already exists")
    baseline, _ = read_summary(INPUTS["baseline_summary"])
    tracking, _ = read_summary(INPUTS["tracking_summary"])
    # The tracked report adds post-run artifact_validation to the original summary.
    # Restore that source serialization and require the tracker's exact recorded hash.
    source_summary = {key: value for key, value in baseline.items() if key != "artifact_validation"}
    source_bytes = (json.dumps(source_summary, indent=2) + "\n").encode("utf-8")
    baseline_digest = hashlib.sha256(source_bytes).hexdigest()
    context = SimpleNamespace(
        video_sha256=baseline["video_sha256"],
        **{key: baseline[key] for key in ("width", "height", "frame_count", "fps")},
    )
    if not 0 <= frame_index < context.frame_count:
        raise ValueError("frame outside the source clip")
    if sha256_file(video) != context.video_sha256:
        raise ValueError("video differs from the saved building baseline")
    floor = baseline["parameters"]["conf"]
    person_class, names = bind_baseline(
        baseline, context, SimpleNamespace(min_detection_confidence=floor)
    )
    bind_tracker(tracking, baseline, baseline_digest, person_class, context)
    detections = FrameStream(
        INPUTS["detections"], DetectionFrame, output_digest(baseline, "detections.jsonl"), context
    )
    tracks = FrameStream(
        INPUTS["tracks"], TrackFrame, output_digest(tracking, "tracks.jsonl"), context
    )
    selected = None
    for detected, tracked in zip(detections, tracks, strict=True):
        validate_detections(detected, names, floor)
        validate_tracks(tracked, detected, person_class)
        if detected.frame_index == frame_index:
            selected = detected, tracked

    import cv2
    import numpy as np

    capture = cv2.VideoCapture(str(video))
    raw_frame = None
    try:
        for index in range(context.frame_count):
            ok, frame = capture.read()
            if not ok or frame.shape[:2] != (context.height, context.width):
                raise ValueError("source video decode/count/dimensions mismatch")
            if index == frame_index:
                raw_frame = frame.copy()
        if capture.read()[0]:
            raise ValueError("source video contains extra frames")
    finally:
        capture.release()

    detected, tracked = selected
    width, height, gap = context.width, context.height, 24
    figure = np.full((height + 180, width * 3 + gap * 4, 3), (28, 24, 19), dtype=np.uint8)
    white, muted, accent = (238, 233, 225), (179, 166, 148), (197, 219, 81)

    def text(label, x, y, scale=0.5, color=white):
        cv2.putText(figure, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)

    text("WORKSITE VISION LAB / BUILDING BASELINE", gap, 29, 0.55, accent)
    text(
        f"Frame {frame_index} | {frame_index / context.fps:.3f} s | "
        "saved outputs, no new inference",
        gap,
        55,
        color=muted,
    )
    panels = [
        ("01 / RAW INPUT", []),
        (
            "02 / YOLO26n PERSON DETECTIONS",
            [d for d in detected.detections if d.class_id == person_class],
        ),
        ("03 / BoT-SORT OUTPUT", tracked.tracks),
    ]
    for panel_index, (label, boxes) in enumerate(panels):
        left, top = gap + panel_index * (width + gap), 102
        text(label, left, 86, 0.44)
        figure[top : top + height, left : left + width] = raw_frame
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy
            x1, x2 = [int(round(max(0, min(width - 1, x)))) for x in (x1, x2)]
            y1, y2 = [int(round(max(0, min(height - 1, y)))) for y in (y1, y2)]
            color = accent if panel_index == 1 else (243, 196, 111)
            cv2.rectangle(figure, (left + x1, top + y1), (left + x2, top + y2), color, 2)
            label = f"Person {box.confidence:.2f}" if panel_index == 1 else f"Track {box.track_id}"
            tx, ty = left + x1, top + max(18, y1 + 18)
            label_width = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.47, 1)[0][0]
            cv2.rectangle(figure, (tx, ty - 16), (tx + label_width + 8, ty + 4), (28, 24, 19), -1)
            text(label, tx + 4, ty, 0.47, color)
    text(
        "Qualitative evidence only. Track IDs are model outputs; "
        "no reference labels or accuracy scores.",
        gap,
        height + 133,
        color=muted,
    )
    text(
        "Source: Akum20 / Wikimedia Commons / CC0. "
        "Modified: resize, resample and prediction overlays.",
        gap,
        height + 158,
        0.45,
        muted,
    )
    output.mkdir(parents=True, exist_ok=False)
    path = output / "figure.png"
    if not cv2.imwrite(str(path), figure):
        raise RuntimeError("figure write failed")
    manifest = {
        "schema_version": 1,
        "frame_index": frame_index,
        "timestamp_seconds": frame_index / context.fps,
        "video_sha256": context.video_sha256,
        "decoded_frame_bgr_sha256": hashlib.sha256(raw_frame.tobytes()).hexdigest(),
        "input_sha256": {name: sha256_file(path) for name, path in INPUTS.items()},
        "baseline_source_summary_sha256": baseline_digest,
        "figure_sha256": sha256_file(path),
        "renderer_sha256": sha256_file(Path(__file__)),
        "rendering_runtime": {"opencv": cv2.__version__, "numpy": np.__version__},
        "source": "https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm",
        "author": "Akum20",
        "license": "CC0-1.0",
        "modifications": ["resizing", "resampling", "prediction overlays", "comparison layout"],
        "accuracy_measured": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(render(args.video, args.output, args.frame), indent=2))
