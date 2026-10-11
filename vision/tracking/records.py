"""Validate frozen input and calculate observations, never ground-truth metrics."""

import math

from vision.detection.records import frame_record


def validate_frame(record, index, summary):
    if record["frame_index"] != index:
        raise ValueError("detection frames must be contiguous and zero-based")
    if not math.isclose(record["timestamp_seconds"], index / summary["fps"], abs_tol=1e-8):
        raise ValueError("detection timestamp mismatch")
    if (record["width"], record["height"]) != (summary["width"], summary["height"]):
        raise ValueError("detection dimensions mismatch")
    names = {int(k): v for k, v in summary["model"]["names"].items()}
    for detection in record["detections"]:
        if names.get(detection["class_id"]) != detection["class_name"]:
            raise ValueError("detection class name mismatch")
    frame_record(
        index,
        summary["fps"],
        [(d["xyxy"], d["confidence"], d["class_id"]) for d in record["detections"]],
        names,
        summary["width"],
        summary["height"],
    )


class TrackObservations:
    def __init__(self):
        self.histories = {}
        self.frames_without_tracks = 0
        self.frames_without_person_detections = 0
        self.person_detections = 0

    def update(self, record):
        index = record["frame_index"]
        self.person_detections += record["person_detection_count"]
        self.frames_without_person_detections += record["person_detection_count"] == 0
        self.frames_without_tracks += not record["tracks"]
        ids = [track["track_id"] for track in record["tracks"]]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate track ID within frame")
        for track_id in ids:
            history = self.histories.setdefault(track_id, [])
            if history and index <= history[-1]:
                raise ValueError("track frames must strictly increase")
            history.append(index)

    def summary(self, fps):
        tracks = []
        for track_id, frames in sorted(self.histories.items()):
            gaps = [
                {"after_frame": a, "before_frame": b, "missing_frames": b - a - 1}
                for a, b in zip(frames, frames[1:], strict=False)
                if b > a + 1
            ]
            tracks.append(
                {
                    "track_id": track_id,
                    "first_frame": frames[0],
                    "last_frame": frames[-1],
                    "observed_frames": len(frames),
                    "span_seconds": (frames[-1] - frames[0] + 1) / fps,
                    "gaps": gaps,
                }
            )
        return {
            "emitted_track_ids": len(tracks),
            "track_box_observations": sum(t["observed_frames"] for t in tracks),
            "person_detection_observations": self.person_detections,
            "frames_without_tracks": self.frames_without_tracks,
            "frames_without_person_detections": self.frames_without_person_detections,
            "within_id_gap_count": sum(len(t["gaps"]) for t in tracks),
            "tracks": tracks,
            "definitions": {
                "emitted_track_ids": "distinct emitted video-local IDs; NOT unique real workers",
                "within_id_gap_count": (
                    "gaps between observations of same ID; NOT fragmentation or ID switches"
                ),
                "span_seconds": "inclusive first-to-last frame span; includes unobserved gaps",
            },
            "ground_truth": None,
            "identity_accuracy_measured": False,
        }
