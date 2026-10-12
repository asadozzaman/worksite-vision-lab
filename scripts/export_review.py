"""Export exact raw frames, switchable predictions and empty reference templates."""

import argparse
import json
from pathlib import Path

from vision.detection.run import file_hash
from vision.evaluation.reference import empty_reference
from vision.evaluation.render import render_editor
from vision.tracking.records import validate_frame


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--tracking", type=Path, nargs="*", default=[])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--attribution", required=True)
    args = p.parse_args()
    summary = json.loads((args.baseline / "summary.json").read_text())
    if summary["video_sha256"] != file_hash(args.video):
        raise ValueError("video checksum mismatch")
    detections = args.baseline / "detections.jsonl"
    if summary["output_hashes"]["detections.jsonl"] != file_hash(detections):
        raise ValueError("detection checksum mismatch")
    frames = [json.loads(line) for line in detections.read_text().splitlines()]
    if len(frames) != summary["frame_count"]:
        raise ValueError("detection count mismatch")
    for index, frame in enumerate(frames):
        validate_frame(frame, index, summary)
    trackers, tracking_hashes = {}, {}
    for folder in args.tracking:
        info = json.loads((folder / "summary.json").read_text())
        path = folder / "tracks.jsonl"
        if info["source_detections_sha256"] != file_hash(detections):
            raise ValueError("tracking uses different detections")
        if info["output_hashes"]["tracks.jsonl"] != file_hash(path):
            raise ValueError("tracking checksum mismatch")
        records = [json.loads(line) for line in path.read_text().splitlines()]
        if len(records) != len(frames) or any(r["frame_index"] != i for i, r in enumerate(records)):
            raise ValueError("tracking frame alignment mismatch")
        trackers[folder.name] = records
        tracking_hashes[folder.name] = file_hash(path)

    import cv2

    args.output.mkdir(parents=True, exist_ok=False)
    images = args.output / "images"
    images.mkdir()
    capture = cv2.VideoCapture(str(args.video))
    hashes = {}
    try:
        for index in range(len(frames)):
            ok, frame = capture.read()
            if not ok:
                raise ValueError("video truncated")
            path = images / f"{index:06d}.jpg"
            if not cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError("cannot write review image")
            hashes[path.name] = file_hash(path)
        if capture.read()[0]:
            raise ValueError("video longer than detection stream")
    finally:
        capture.release()
    manifest = {
        "schema_version": 1,
        "split": "development",
        "title": args.title,
        "video_sha256": summary["video_sha256"],
        "detections_sha256": file_hash(detections),
        "tracking_sha256": tracking_hashes,
        "frame_count": len(frames),
        "fps": summary["fps"],
        "width": summary["width"],
        "height": summary["height"],
        "attribution": args.attribution,
        "image_sha256": hashes,
        "reference_status": "unreviewed; no accuracy metrics authorized",
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    reference = empty_reference(manifest, file_hash(args.output / "manifest.json")).model_dump(
        mode="json"
    )
    (args.output / "reference-template.json").write_text(
        json.dumps(reference, indent=2) + "\n", encoding="utf-8"
    )
    bundle = {**manifest, "frames": frames, "trackers": trackers}
    (args.output / "index.html").write_text(render_editor(bundle, reference), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(frames), "reviewed": False}))


if __name__ == "__main__":
    main()
