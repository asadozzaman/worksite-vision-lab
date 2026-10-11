import copy

import pytest
from pydantic import ValidationError

from vision.tracking.config import TrackerConfig
from vision.tracking.records import TrackObservations, validate_frame


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track_low_thresh": 0.4},
        {"new_track_thresh": 0.2},
        {"track_buffer": 0},
        {"with_reid": True},
        {"gmc_method": "unknown"},
        {"match_thresh": float("nan")},
        {"unexpected": 1},
    ],
)
def test_invalid_tracker_settings(kwargs):
    with pytest.raises(ValidationError):
        TrackerConfig(tracker_type="bytetrack", **kwargs)


@pytest.fixture
def input_pair():
    summary = {"fps": 25, "width": 100, "height": 100, "model": {"names": {"6": "Person"}}}
    frame = {
        "frame_index": 0,
        "timestamp_seconds": 0,
        "width": 100,
        "height": 100,
        "detections": [
            {"class_id": 6, "class_name": "Person", "confidence": 0.9, "xyxy": [10, 10, 50, 50]}
        ],
    }
    return frame, summary


def test_frame_validation(input_pair):
    frame, summary = input_pair
    validate_frame(frame, 0, summary)
    for field, value in [("frame_index", 1), ("timestamp_seconds", 0.1), ("width", 101)]:
        bad = {**frame, field: value}
        with pytest.raises(ValueError):
            validate_frame(bad, 0, summary)
    bad = copy.deepcopy(frame)
    bad["detections"][0]["class_name"] = "helmet"
    with pytest.raises(ValueError, match="class name"):
        validate_frame(bad, 0, summary)


def test_observation_gaps_are_not_identity_errors():
    observations = TrackObservations()
    for index, ids, detections in [(0, [1], 1), (1, [], 0), (2, [1, 2], 2), (3, [2], 2)]:
        observations.update(
            {
                "frame_index": index,
                "person_detection_count": detections,
                "tracks": [{"track_id": i} for i in ids],
            }
        )
    result = observations.summary(25)
    assert result["emitted_track_ids"] == 2
    assert result["track_box_observations"] == 4
    assert result["within_id_gap_count"] == 1
    assert result["frames_without_tracks"] == 1
    assert result["person_detection_observations"] == 5
    assert result["ground_truth"] is None
    assert result["identity_accuracy_measured"] is False


def test_duplicate_id_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        TrackObservations().update(
            {
                "frame_index": 0,
                "person_detection_count": 2,
                "tracks": [{"track_id": 1}, {"track_id": 1}],
            }
        )
