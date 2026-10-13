"""Software fixtures for evaluator contract tests; never research footage or human labels."""

import copy
import json

import pytest

from vision.evaluation.config import EvaluationConfig
from vision.evaluation.reference import empty_reference, freeze_reference
from vision.provenance import sha256_file


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def save_records(bundle, kind, records):
    folder = bundle["baseline"] if kind == "detection" else bundle[kind]
    name = "detections.jsonl" if kind == "detection" else "tracks.jsonl"
    path = folder / name
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    summary = json.loads((folder / "summary.json").read_bytes())
    summary["output_hashes"][name] = sha256_file(path)
    write_json(folder / "summary.json", summary)
    if kind == "detection":
        for tracker in ("bytetrack", "botsort"):
            source = bundle[tracker] / "summary.json"
            updated = json.loads(source.read_bytes())
            updated["source_detections_sha256"] = sha256_file(path)
            updated["source_baseline_summary_sha256"] = sha256_file(folder / "summary.json")
            write_json(source, updated)


def get_records(bundle, kind):
    folder = bundle["baseline"] if kind == "detection" else bundle[kind]
    name = "detections.jsonl" if kind == "detection" else "tracks.jsonl"
    return [json.loads(line) for line in (folder / name).read_text().splitlines()]


def refreeze(bundle, doc):
    write_json(bundle["draft"], doc)
    folder = bundle["root"] / f"frozen-{len(list(bundle['root'].glob('frozen-*')))}"
    freeze_reference(bundle["draft"], bundle["manifest"], bundle["images"], folder)
    bundle["reference"] = folder


@pytest.fixture
def evaluation_source(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    hashes = {}
    for index in range(3):
        path = images / f"{index:06d}.jpg"
        path.write_bytes(f"hash fixture {index}; not a real JPEG".encode())
        hashes[path.name] = sha256_file(path)
    video = tmp_path / "fixture.bin"
    video.write_bytes(b"software video identity fixture; not evaluation footage")
    manifest = {
        "video_sha256": sha256_file(video),
        "split": "development",
        "width": 100,
        "height": 100,
        "fps": 25.0,
        "frame_count": 3,
        "image_sha256": hashes,
    }
    manifest_path = tmp_path / "manifest.json"
    write_json(manifest_path, manifest)
    reference = empty_reference(manifest, sha256_file(manifest_path)).model_dump(mode="json")
    # Simulates a declaration solely to exercise the gate. It is not a real annotation claim.
    reference.update(
        reviewer="Software fixture: simulated reviewer declaration",
        complete=True,
        human_attested=True,
        revision=1,
    )
    reference["history"] = [
        {
            "revision": 1,
            "at": "2026-10-12T00:00:00Z",
            "action": "software_fixture",
            "frame_index": None,
        }
    ]
    reference["identities"] = [{"person_id": "p001", "notes": "Software fixture only"}]
    person = {
        "person_id": "p001",
        "xyxy": [10.0, 10.0, 30.0, 70.0],
        "visibility": "visible",
        "truncated": False,
        "ignore": False,
        "notes": "Software fixture only",
    }
    for frame in reference["frames"]:
        frame.update(
            reviewed=True, reviewed_by=reference["reviewer"], people=[copy.deepcopy(person)]
        )
    draft = tmp_path / "draft.json"
    baseline = tmp_path / "detector"
    baseline.mkdir()
    detections = [
        {
            "frame_index": i,
            "timestamp_seconds": i / 25,
            "width": 100,
            "height": 100,
            "detections": [
                {
                    "class_id": 6,
                    "class_name": "Person",
                    "confidence": 0.9,
                    "xyxy": [10.0, 10.0, 30.0, 70.0],
                },
                {
                    "class_id": 0,
                    "class_name": "helmet",
                    "confidence": 0.8,
                    "xyxy": [10.0, 10.0, 20.0, 20.0],
                },
            ],
        }
        for i in range(3)
    ]
    path = baseline / "detections.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in detections), encoding="utf-8")
    summary = {
        "status": "completed",
        "video_sha256": manifest["video_sha256"],
        "width": 100,
        "height": 100,
        "fps": 25.0,
        "frame_count": 3,
        "model": {"names": {"0": "helmet", "6": "Person"}, "sha256": "c" * 64},
        "parameters": {"conf": 0.25},
        "output_hashes": {"detections.jsonl": sha256_file(path)},
    }
    write_json(baseline / "summary.json", summary)
    bundle = {
        "root": tmp_path,
        "draft": draft,
        "images": images,
        "video": video,
        "manifest": manifest_path,
        "baseline": baseline,
        "output": tmp_path / "result",
    }
    for kind, identity in (("bytetrack", 11), ("botsort", 22)):
        folder = tmp_path / kind
        folder.mkdir()
        records = [
            {
                "frame_index": i,
                "timestamp_seconds": i / 25,
                "width": 100,
                "height": 100,
                "person_detection_count": 1,
                "tracks": [
                    {
                        "track_id": identity,
                        "class_id": 6,
                        "confidence": 0.9,
                        "xyxy": [10.0, 10.0, 30.0, 70.0],
                        "detection_index": 0,
                    }
                ],
            }
            for i in range(3)
        ]
        tracks = folder / "tracks.jsonl"
        tracks.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        info = {
            "status": "completed",
            "tracker": {"tracker_type": kind},
            "person_class_id": 6,
            "source_video_sha256": manifest["video_sha256"],
            "source_detections_sha256": sha256_file(path),
            "source_baseline_summary_sha256": sha256_file(baseline / "summary.json"),
            "source_model": summary["model"],
            "source_detector_parameters": summary["parameters"],
            "width": 100,
            "height": 100,
            "fps": 25.0,
            "frame_count": 3,
            "output_hashes": {"tracks.jsonl": sha256_file(tracks)},
        }
        write_json(folder / "summary.json", info)
        bundle[kind] = folder
    config = tmp_path / "config.json"
    write_json(config, EvaluationConfig().model_dump(mode="json"))
    bundle["config"] = config
    refreeze(bundle, reference)
    return bundle
