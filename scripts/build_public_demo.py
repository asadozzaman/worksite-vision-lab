"""Export an allowlisted, source-verified static demo; never publish local user labels."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from vision.evaluation.reference import verify_reference_images
from vision.evaluation.sources import (
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
FRAMES = (0, 25, 50, 75, 100, 130)


def export_samples(images, manifest_path, destination):
    manifest = json.loads(manifest_path.read_bytes())
    baseline_path = ROOT / "experiments/results/building-baseline.json"
    baseline = json.loads(baseline_path.read_bytes())
    context = SimpleNamespace(
        video_sha256=baseline["video_sha256"],
        **{key: baseline[key] for key in ("width", "height", "fps", "frame_count")},
    )
    for key in ("video_sha256", "width", "height", "fps", "frame_count"):
        if manifest[key] != getattr(context, key):
            raise ValueError("review image manifest differs from building baseline")
    detections_path = ROOT / "experiments/results/building-baseline.jsonl"
    if manifest["detections_sha256"] != output_digest(baseline, "detections.jsonl"):
        raise ValueError("review images bind to different detections")
    verify_reference_images(context, manifest, images)
    floor = baseline["parameters"]["conf"]
    person_class, names = bind_baseline(
        baseline, context, SimpleNamespace(min_detection_confidence=floor)
    )
    original_summary = {k: v for k, v in baseline.items() if k != "artifact_validation"}
    source_digest = hashlib.sha256(
        (json.dumps(original_summary, indent=2) + "\n").encode()
    ).hexdigest()
    summaries, records, input_hashes = {}, {}, {"detections": sha256_file(detections_path)}
    for name in ("bytetrack", "botsort"):
        path = ROOT / f"experiments/results/tracking/building-{name}.json"
        summary = json.loads(path.read_bytes())
        bind_tracker(summary, baseline, source_digest, person_class, context)
        summaries[name] = summary
        track_path = ROOT / f"experiments/results/tracking/building-{name}.jsonl"
        records[name] = iter(
            FrameStream(track_path, TrackFrame, output_digest(summary, "tracks.jsonl"), context)
        )
        input_hashes[name] = sha256_file(track_path)
    sampled = []
    for detected in FrameStream(
        detections_path, DetectionFrame, output_digest(baseline, "detections.jsonl"), context
    ):
        validate_detections(detected, names, floor)
        tracked = {name: next(stream) for name, stream in records.items()}
        for frame in tracked.values():
            validate_tracks(frame, detected, person_class)
        if detected.frame_index in FRAMES:
            sampled.append(
                {
                    "frame_index": detected.frame_index,
                    "timestamp_seconds": detected.timestamp_seconds,
                    "image": f"assets/frames/{detected.frame_index:06d}.jpg",
                    "image_sha256": manifest["image_sha256"][f"{detected.frame_index:06d}.jpg"],
                    "detections": [
                        {"source_index": i, **box.model_dump()}
                        for i, box in enumerate(detected.detections)
                        if box.class_id == person_class
                    ],
                    "tracks": {
                        name: frame.model_dump()["tracks"] for name, frame in tracked.items()
                    },
                }
            )
    for stream in records.values():
        try:
            next(stream)
        except StopIteration:
            pass
        else:
            raise ValueError("extra tracking frames")
    assets = json.loads((ROOT / "docs/assets.json").read_bytes())["assets"]
    source = next(asset for asset in assets if asset["id"] == "commons-building-site")
    if source["license_status"] != "verified" or source["redistribution"] != "verified":
        raise ValueError("public image redistribution has not been verified")
    if source["license_url"] != "https://creativecommons.org/publicdomain/zero/1.0/":
        raise ValueError("public demo only supports the reviewed CC0 building source")
    if destination.exists():
        raise FileExistsError("sample output already exists")
    destination.mkdir(parents=True)
    for index in FRAMES:
        shutil.copyfile(images / f"{index:06d}.jpg", destination / f"{index:06d}.jpg")
    return {
        "schema_version": 1,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "scope": "saved_person_predictions_only",
        "accuracy": None,
        "clip": {
            "name": "Building site",
            "width": context.width,
            "height": context.height,
            "fps": context.fps,
            "frame_count": context.frame_count,
            "video_sha256": context.video_sha256,
            "source_url": source["source_url"],
            "author": source["creator"],
            "license": "CC0-1.0",
            "license_url": source["license_url"],
            "modifications": ["resizing", "resampling", "JPEG frame extraction", "overlays"],
        },
        "model": {
            "name": "YOLO26n PPE / Person class",
            "sha256": baseline["model"]["sha256"],
            "person_class_id": person_class,
            "confidence_floor": floor,
            "inference_size": baseline["parameters"]["imgsz"],
        },
        "input_sha256": input_hashes,
        "baseline_source_summary_sha256": source_digest,
        "frames": sampled,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    payload = export_samples(args.images, args.manifest, args.site / "assets/frames")
    (args.site / "results.json").write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
    shutil.copyfile(
        ROOT / "docs/figures/building-baseline/figure.png",
        args.site / "assets/baseline-comparison.png",
    )
    print(json.dumps({"sampled_frames": len(payload["frames"]), "scope": payload["scope"]}))
