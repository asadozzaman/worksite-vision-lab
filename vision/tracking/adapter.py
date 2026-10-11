"""Small version-pinned adapter; one instance per sequential video stream."""

import math
from types import SimpleNamespace


class PersonTracker:
    def __init__(self, config, person_class_id, width, height):
        import ultralytics
        from ultralytics.trackers.bot_sort import BOTSORT
        from ultralytics.trackers.byte_tracker import BYTETracker

        if ultralytics.__version__ != "8.4.173":
            raise RuntimeError("tracker adapter requires ultralytics==8.4.173")
        args = SimpleNamespace(**config.model_dump())
        tracker_class = BYTETracker if config.tracker_type == "bytetrack" else BOTSORT
        self.tracker = tracker_class(args)
        self.person_class_id = person_class_id
        self.width = width
        self.height = height

    def update(self, detections, image):
        import numpy as np
        from ultralytics.engine.results import Boxes

        people = [(i, d) for i, d in enumerate(detections) if d["class_id"] == self.person_class_id]
        data = np.asarray(
            [[*d["xyxy"], d["confidence"], d["class_id"]] for _, d in people], dtype=np.float32
        ).reshape(-1, 6)
        # Empty updates are essential: loss age and motion compensation still advance.
        rows = self.tracker.update(Boxes(data, (self.height, self.width)), image)
        tracks = []
        for row in rows:
            x1, y1, x2, y2, track_id, score, class_id, detection_index = map(float, row)
            if not all(math.isfinite(v) for v in row):
                raise ValueError("non-finite tracker output")
            if int(class_id) != self.person_class_id or track_id <= 0 or track_id != int(track_id):
                raise ValueError("invalid tracker identity or class")
            index = int(detection_index)
            if detection_index != index or not 0 <= index < len(people):
                raise ValueError("tracker returned invalid detection index")
            if x2 <= x1 or y2 <= y1:
                raise ValueError("degenerate tracker box")
            tracks.append(
                {
                    "track_id": int(track_id),
                    "class_id": int(class_id),
                    "confidence": score,
                    # Kalman estimates may extend beyond the image; retain raw geometry.
                    "xyxy": [x1, y1, x2, y2],
                    "detection_index": people[index][0],
                }
            )
        return tracks, len(people)
