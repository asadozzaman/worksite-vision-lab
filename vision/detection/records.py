"""Pure validation/serialization of video-local observations."""

import math


def frame_record(index, fps, detections, names, width, height):
    if index < 0 or not math.isfinite(fps) or fps <= 0:
        raise ValueError("invalid frame index or frame rate")
    boxes = []
    for xyxy, confidence, class_id in detections:
        values = [float(v) for v in xyxy]
        if len(values) != 4 or not all(math.isfinite(v) for v in values):
            raise ValueError("invalid box coordinates")
        if class_id not in names or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("invalid class or confidence")
        x1, y1, x2, y2 = values
        if not (0 <= x1 <= x2 <= width and 0 <= y1 <= y2 <= height):
            raise ValueError("box outside normalized input")
        boxes.append(
            {
                "class_id": class_id,
                "class_name": names[class_id],
                "confidence": float(confidence),
                "xyxy": values,
            }
        )
    return {
        "frame_index": index,
        "timestamp_seconds": index / fps,
        "width": width,
        "height": height,
        "detections": boxes,
    }
