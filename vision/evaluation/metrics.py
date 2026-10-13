"""Person detection counts and pinned upstream CLEAR/Identity metrics."""

import importlib.metadata
import math
from pathlib import Path

from vision.evaluation.geometry import iou_matrix, match_detection, prepare_predictions
from vision.provenance import sha256_file

VERSIONS = {"motmetrics": "1.4.0", "numpy": "1.26.4", "scipy": "1.15.3", "pandas": "2.3.3"}
METRICS = [
    "num_frames",
    "num_objects",
    "num_predictions",
    "num_detections",
    "num_switches",
    "num_misses",
    "num_false_positives",
    "num_fragmentations",
    "idtp",
    "idfp",
    "idfn",
    "idf1",
    "idp",
    "idr",
    "mota",
    "motp",
    "precision",
    "recall",
]
COUNTS = set(METRICS[:11])


def evaluation_runtime():
    for package, expected in VERSIONS.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError("install requirements/evaluation.lock.txt for evaluation") from exc
        if actual != expected:
            raise ValueError(f"evaluation requires {package}=={expected}; found {actual}")
    import motmetrics as mm

    return {
        **VERSIONS,
        "assignment_solver": "scipy",
        "motmetrics_source_sha256": {
            name: sha256_file(Path(getattr(mm, name).__file__))
            for name in ("mot", "metrics", "lap")
        },
    }


def scores(tp, fp, fn):
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


class DetectionMetrics:
    def __init__(self, config):
        self.config = config
        self.tp = self.fp = self.fn = self.excluded = self.frames = 0

    def update(self, frame, predictions):
        people, ignored, kept, excluded = prepare_predictions(
            frame.people, predictions, self.config
        )
        matrix = iou_matrix(people, kept)
        pairs = match_detection(matrix, self.config.match_iou)
        matched_people, matched_predictions = {p for p, _ in pairs}, {d for _, d in pairs}
        self.tp += len(pairs)
        self.fp += len(kept) - len(pairs)
        self.fn += len(people) - len(pairs)
        self.excluded += len(excluded)
        self.frames += 1
        return {
            "matches": [
                {
                    "person_id": people[p].person_id,
                    "prediction_index": kept[d]["index"],
                    "iou": float(matrix[p, d]),
                }
                for p, d in pairs
            ],
            "false_negative_person_ids": [
                p.person_id for i, p in enumerate(people) if i not in matched_people
            ],
            "false_positive_prediction_indexes": [
                d["index"] for i, d in enumerate(kept) if i not in matched_predictions
            ],
            "excluded_prediction_indexes": [d["index"] for d in excluded],
            "ignored_reference_boxes": len(ignored),
        }

    def summary(self):
        return {
            **scores(self.tp, self.fp, self.fn),
            "evaluated_frames": self.frames,
            "ground_truth_person_observations": self.tp + self.fn,
            "scored_predictions": self.tp + self.fp,
            "excluded_predictions": self.excluded,
        }


class TrackingMetrics:
    def __init__(self, config, identities):
        import motmetrics as mm

        self.config = config
        self.identity_map = {p: i + 1 for i, p in enumerate(sorted(identities))}
        self.reverse = {v: k for k, v in self.identity_map.items()}
        self.accumulator = mm.MOTAccumulator(auto_id=False, max_switch_time=float("inf"))
        self.previous = {}
        self.excluded = 0

    def update(self, frame, predictions):
        import motmetrics as mm
        import numpy as np

        people, ignored, kept, excluded = prepare_predictions(
            frame.people, predictions, self.config
        )
        matrix = iou_matrix(people, kept)
        distances = np.where(matrix >= self.config.match_iou, 1.0 - matrix, np.nan)
        with mm.lap.set_default_solver("scipy"):
            self.accumulator.update(
                [self.identity_map[p.person_id] for p in people],
                [d["track_id"] for d in kept],
                distances,
                frameid=frame.frame_index,
            )
        self.excluded += len(excluded)
        events = self.accumulator.mot_events
        events = events[events.index.get_level_values("FrameId") == frame.frame_index]
        matches, switches, misses, false_positives = [], [], [], []
        for event in events.itertuples():
            if event.Type in ("MATCH", "SWITCH"):
                person_id, track_id = self.reverse[int(event.OId)], int(event.HId)
                matches.append(
                    {"person_id": person_id, "track_id": track_id, "iou": 1.0 - float(event.D)}
                )
                if event.Type == "SWITCH":
                    switches.append(
                        {
                            "person_id": person_id,
                            "previous_track_id": self.previous[person_id],
                            "track_id": track_id,
                        }
                    )
                self.previous[person_id] = track_id
            elif event.Type == "MISS":
                misses.append(self.reverse[int(event.OId)])
            elif event.Type == "FP":
                false_positives.append(int(event.HId))
        return {
            "matches": matches,
            "identity_switches": switches,
            "false_negative_person_ids": misses,
            "false_positive_track_ids": false_positives,
            "excluded_track_ids": [d["track_id"] for d in excluded],
            "ignored_reference_boxes": len(ignored),
        }

    def summary(self):
        import motmetrics as mm

        with mm.lap.set_default_solver("scipy"):
            raw = mm.metrics.create().compute(
                self.accumulator, metrics=METRICS, return_dataframe=False
            )
        result = {
            key: int(value) if key in COUNTS else float(value) if math.isfinite(value) else None
            for key, value in raw.items()
        }
        if not result["num_objects"]:
            for key in ("mota", "idf1", "idp", "idr"):
                result[key] = None
        result["mean_matched_iou"] = 1.0 - result["motp"] if result["motp"] is not None else None
        result.update(
            scores(result["num_detections"], result["num_false_positives"], result["num_misses"])
        )
        result["excluded_predictions"] = self.excluded
        result["identity_evaluable"] = result["num_objects"] > 0
        return result
