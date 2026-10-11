import math

import pytest

from vision.detection.records import frame_record


def test_empty_frames_preserve_alignment():
    record = frame_record(10, 25, [], {6: "Person"}, 360, 640)
    assert record["timestamp_seconds"] == 0.4
    assert record["detections"] == []


def test_class_names_and_coordinates_come_from_model():
    record = frame_record(0, 25, [([1, 2, 10, 20], 0.8, 6)], {6: "Person"}, 360, 640)
    box = record["detections"][0]
    assert box["class_name"] == "Person"
    assert box["xyxy"] == [1, 2, 10, 20]


@pytest.mark.parametrize(
    "box,confidence,cls",
    [
        ([0, 0, 361, 640], 0.8, 6),
        ([10, 0, 5, 640], 0.8, 6),
        ([0, 0, math.nan, 640], 0.8, 6),
        ([0, 0, 1], 0.8, 6),
        ([0, 0, 10, 10], math.nan, 6),
        ([0, 0, 10, 10], 0.8, 7),
    ],
)
def test_reject_invalid_model_outputs(box, confidence, cls):
    with pytest.raises(ValueError):
        frame_record(0, 25, [(box, confidence, cls)], {6: "Person"}, 360, 640)


@pytest.mark.parametrize("fps", [0, -1, math.nan, math.inf])
def test_reject_invalid_frame_rates(fps):
    with pytest.raises(ValueError):
        frame_record(0, fps, [], {}, 360, 640)
