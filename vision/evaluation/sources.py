"""Bounded, strict parsing of completed prediction runs and source alignment."""

import hashlib
import json
import math
import re
from pathlib import Path

from pydantic import Field

from vision.config import resolve_person_class
from vision.evaluation.reference import StrictModel

MAX_LINE_BYTES = 8 * 1024 * 1024


class Detection(StrictModel):
    class_id: int = Field(ge=0)
    class_name: str
    confidence: float = Field(ge=0, le=1)
    xyxy: list[float] = Field(min_length=4, max_length=4)


class DetectionFrame(StrictModel):
    frame_index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    detections: list[Detection] = Field(max_length=1000)


class Track(StrictModel):
    # motmetrics uses float64 event columns: keep identity integers exactly representable.
    track_id: int = Field(gt=0, le=2**53 - 1)
    class_id: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    xyxy: list[float] = Field(min_length=4, max_length=4)
    detection_index: int = Field(ge=0)


class TrackFrame(StrictModel):
    frame_index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    person_detection_count: int = Field(ge=0)
    tracks: list[Track] = Field(max_length=1000)


def read_summary(folder):
    path = folder / "summary.json"
    if path.stat().st_size > MAX_LINE_BYTES:
        raise ValueError("run summary exceeds 8 MiB")
    raw = path.read_bytes()
    summary = json.loads(raw)
    if not isinstance(summary, dict) or summary.get("status") != "completed":
        raise ValueError(f"evaluation requires completed run: {folder.name}")
    return summary, hashlib.sha256(raw).hexdigest()


def require(summary, key):
    if key not in summary:
        raise ValueError(f"run summary missing {key}")
    return summary[key]


def output_digest(summary, filename):
    hashes = require(summary, "output_hashes")
    if not isinstance(hashes, dict):
        raise ValueError("run output_hashes must be an object")
    digest = hashes.get(filename)
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError(f"missing or invalid output checksum: {filename}")
    return digest


def bind_baseline(summary, reference, config):
    if require(summary, "video_sha256") != reference.video_sha256:
        raise ValueError("detection run uses a different video")
    for key in ("width", "height", "frame_count", "fps"):
        value = require(summary, key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value != getattr(reference, key)
        ):
            raise ValueError(f"detection run {key} mismatch")
    model = require(summary, "model")
    if not isinstance(model, dict) or not isinstance(model.get("names"), dict):
        raise ValueError("detection run is missing class names")
    if any(
        not isinstance(key, str)
        or not re.fullmatch(r"0|[1-9][0-9]*", key)
        or not isinstance(value, str)
        or not value.strip()
        for key, value in model["names"].items()
    ):
        raise ValueError("invalid class name mapping")
    names = {int(key): value for key, value in model["names"].items()}
    person_class = resolve_person_class(names)
    parameters = require(summary, "parameters")
    floor = parameters.get("conf") if isinstance(parameters, dict) else None
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not 0 <= floor <= 1:
        raise ValueError("missing or invalid source detector confidence")
    if config.min_detection_confidence < floor:
        raise ValueError("evaluation confidence is below the saved detector floor")
    return person_class, names


def bind_tracker(summary, baseline, baseline_digest, person_class, reference):
    for key, value in (
        ("source_video_sha256", reference.video_sha256),
        ("source_detections_sha256", output_digest(baseline, "detections.jsonl")),
        ("source_baseline_summary_sha256", baseline_digest),
        ("source_model", require(baseline, "model")),
        ("source_detector_parameters", require(baseline, "parameters")),
        ("person_class_id", person_class),
        *((k, getattr(reference, k)) for k in ("width", "height", "fps", "frame_count")),
    ):
        if require(summary, key) != value:
            raise ValueError(
                f"tracker {key} mismatch; comparisons require identical detection inputs"
            )
    tracker = require(summary, "tracker")
    if not isinstance(tracker, dict) or tracker.get("tracker_type") not in ("bytetrack", "botsort"):
        raise ValueError("unsupported or missing tracker type")
    return tracker["tracker_type"]


class FrameStream:
    """Hash the exact bytes being parsed, then verify count and digest at exhaustion."""

    def __init__(self, path: Path, schema, expected_digest, reference):
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise ValueError("missing output checksum")
        self.path, self.schema = path, schema
        self.expected_digest, self.reference = expected_digest, reference
        self.digest = None

    def __iter__(self):
        digest, count = hashlib.sha256(), 0
        with self.path.open("rb") as stream:
            while raw := stream.readline(MAX_LINE_BYTES + 1):
                if len(raw) > MAX_LINE_BYTES:
                    raise ValueError("prediction record exceeds 8 MiB")
                if count >= self.reference.frame_count:
                    raise ValueError("prediction stream has extra frames")
                digest.update(raw)
                frame = self.schema.model_validate_json(raw)
                if frame.frame_index != count:
                    raise ValueError("prediction frames must be contiguous and zero-based")
                if (frame.width, frame.height) != (self.reference.width, self.reference.height):
                    raise ValueError("prediction frame dimensions mismatch")
                if not math.isclose(
                    frame.timestamp_seconds, count / self.reference.fps, rel_tol=0, abs_tol=1e-9
                ):
                    raise ValueError("prediction timestamp mismatch")
                count += 1
                yield frame
        if count != self.reference.frame_count:
            raise ValueError("prediction stream is truncated")
        self.digest = digest.hexdigest()
        if self.digest != self.expected_digest:
            raise ValueError(f"prediction checksum mismatch: {self.path.name}")


def validate_detections(frame, names, detector_floor):
    for box in frame.detections:
        if names.get(box.class_id) != box.class_name:
            raise ValueError("prediction class ID/name mismatch")
        x1, y1, x2, y2 = box.xyxy
        if not (0 <= x1 < x2 <= frame.width and 0 <= y1 < y2 <= frame.height):
            raise ValueError("detection geometry is invalid or outside the image")
        if box.confidence + 1e-7 < detector_floor:
            raise ValueError("detection below recorded detector floor")


def validate_tracks(frame, detection_frame, person_class):
    people = [d for d in detection_frame.detections if d.class_id == person_class]
    if frame.person_detection_count != len(people):
        raise ValueError("tracker person detection count mismatch")
    ids, indexes = [], []
    for track in frame.tracks:
        ids.append(track.track_id)
        indexes.append(track.detection_index)
        x1, y1, x2, y2 = track.xyxy
        if x1 >= x2 or y1 >= y2:
            raise ValueError("invalid tracker box geometry")
        if track.class_id != person_class or track.detection_index >= len(
            detection_frame.detections
        ):
            raise ValueError("tracker class or detection index mismatch")
        source = detection_frame.detections[track.detection_index]
        if source.class_id != person_class or abs(track.confidence - source.confidence) > 1e-6:
            raise ValueError("tracker observation differs from source detection")
    if len(set(ids)) != len(ids) or len(set(indexes)) != len(indexes):
        raise ValueError("duplicate tracker ID or source detection within frame")
