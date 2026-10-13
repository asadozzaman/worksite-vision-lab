"""Hand-checkable synthetic examples validate metric behavior, not video accuracy."""

import pytest

pytest.importorskip("motmetrics")
import numpy as np

from vision.evaluation.config import EvaluationConfig
from vision.evaluation.geometry import (
    clip_box,
    iou,
    match_detection,
    prediction_ioa,
    prepare_predictions,
)
from vision.evaluation.metrics import DetectionMetrics, TrackingMetrics, evaluation_runtime
from vision.evaluation.reference import PersonBox, ReferenceFrame


def person(person_id="p001", ignore=False, box=None):
    return PersonBox(
        person_id=person_id,
        xyxy=box or [0.0, 0.0, 10.0, 10.0],
        ignore=ignore,
        notes="Software fixture exclusion" if ignore else "",
    )


def frame(index, people=None):
    return ReferenceFrame(frame_index=index, people=people if people is not None else [person()])


def prediction(index=0, track_id=1, box=None):
    return {"index": index, "track_id": track_id, "xyxy": box or [0, 0, 10, 10]}


def test_pinned_runtime_and_geometry():
    assert evaluation_runtime()["assignment_solver"] == "scipy"
    assert iou([0, 0, 10, 10], [0, 0, 5, 10]) == 0.5
    assert prediction_ioa([0, 0, 5, 10], [0, 0, 10, 10]) == 1
    assert clip_box([-10, 0, 5, 20], 10, 10) == [0, 0, 5, 10]
    assert iou([0, 0, 0, 10], [0, 0, 10, 10]) == 0


def test_assignment_maximizes_pair_count_before_total_iou():
    # Greedy or ungated sum-IoU prefers one TP at .99 to two TPs at .4 each.
    matrix = np.asarray([[0.99, 0.4], [0.4, 0.0]])
    assert set(match_detection(matrix, 0.4)) == {(0, 1), (1, 0)}
    assert match_detection(np.zeros((0, 1)), 0.5) == []
    assert match_detection(np.asarray([[0.5]]), 0.5) == [(0, 0)]


def test_ignore_cannot_hide_duplicates_of_valid_person():
    people = [person(), person("p002", ignore=True)]
    predictions = [prediction(), prediction(index=1, track_id=2)]
    _, _, kept, ignored = prepare_predictions(people, predictions, EvaluationConfig())
    assert len(kept) == 2 and not ignored
    counter = DetectionMetrics(EvaluationConfig())
    counter.update(frame(0, people), predictions)
    assert counter.summary()["false_positives"] == 1


def test_ignore_ioa_removes_many_covered_predictions_but_not_background():
    people = [person(None, ignore=True, box=[0.0, 0.0, 100.0, 100.0])]
    predictions = [
        prediction(),
        prediction(index=1, track_id=2),
        prediction(index=2, track_id=3, box=[110, 0, 120, 10]),
    ]
    valid, _, kept, excluded = prepare_predictions(people, predictions, EvaluationConfig())
    assert not valid and [p["track_id"] for p in kept] == [3]
    assert [p["track_id"] for p in excluded] == [1, 2]


def test_detection_duplicates_misses_and_empty_frame_denominators():
    counter = DetectionMetrics(EvaluationConfig())
    counter.update(frame(0), [prediction(), prediction(index=1)])
    counter.update(frame(1), [])
    result = counter.summary()
    assert (result["true_positives"], result["false_positives"], result["false_negatives"]) == (
        1,
        1,
        1,
    )
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    empty = DetectionMetrics(EvaluationConfig())
    empty.update(frame(0, []), [])
    assert empty.summary()["f1"] is None


def test_identity_switch_and_global_idf1_hand_calculation():
    counter = TrackingMetrics(EvaluationConfig(), ["p001"])
    counter.update(frame(0), [prediction(track_id=10)])
    event = counter.update(frame(1), [prediction(track_id=20)])
    assert event["identity_switches"] == [
        {"person_id": "p001", "previous_track_id": 10, "track_id": 20}
    ]
    result = counter.summary()
    # One GT identity, two predicted identities: global mapping explains only one observation.
    assert result["idtp"] == result["idfp"] == result["idfn"] == 1
    assert result["idf1"] == result["mota"] == 0.5
    assert result["num_switches"] == 1
    assert result["mean_matched_iou"] == 1


def test_gap_with_same_identity_is_fragmentation_without_switch():
    counter = TrackingMetrics(EvaluationConfig(), ["p001"])
    counter.update(frame(0), [prediction()])
    counter.update(frame(1), [])
    counter.update(frame(2), [prediction()])
    result = counter.summary()
    assert result["num_switches"] == 0 and result["num_fragmentations"] == 1
    assert result["num_misses"] == 1 and result["idf1"] == pytest.approx(0.8)


def test_reappearance_after_absence_retains_switch_history():
    counter = TrackingMetrics(EvaluationConfig(), ["p001"])
    counter.update(frame(0), [prediction(track_id=10)])
    counter.update(frame(1, []), [])
    counter.update(frame(2), [prediction(track_id=20)])
    assert counter.summary()["num_switches"] == 1


def test_empty_frames_and_no_gt_identity_ratios_are_null():
    counter = TrackingMetrics(EvaluationConfig(), [])
    counter.update(frame(0, []), [])
    counter.update(frame(1, []), [prediction()])
    result = counter.summary()
    assert result["num_frames"] == 2 and result["num_false_positives"] == 1
    assert result["idf1"] is None and result["mota"] is None
    assert result["precision"] == 0 and result["recall"] is None


def test_clear_continuity_preferred_over_framewise_largest_iou():
    counter = TrackingMetrics(EvaluationConfig(match_iou=0.25), ["p001", "p002"])
    people = [person(box=[0.0, 0.0, 10.0, 10.0]), person("p002", box=[5.0, 0.0, 15.0, 10.0])]
    counter.update(
        frame(0, people),
        [prediction(track_id=1), prediction(index=1, track_id=2, box=[5, 0, 15, 10])],
    )
    # Swapped, overlapping geometry still meets gate for original associations.
    event = counter.update(
        frame(1, people),
        [prediction(track_id=1, box=[5, 0, 15, 10]), prediction(index=1, track_id=2)],
    )
    assert not event["identity_switches"]
    assert [(m["person_id"], m["track_id"]) for m in event["matches"]] == [("p001", 1), ("p002", 2)]


def test_no_overlap_yields_misses_false_positives_and_negative_mota():
    counter = TrackingMetrics(EvaluationConfig(), ["p001"])
    counter.update(
        frame(0),
        [
            prediction(track_id=1, box=[20, 0, 30, 10]),
            prediction(index=1, track_id=2, box=[40, 0, 50, 10]),
        ],
    )
    result = counter.summary()
    assert result["mota"] == -2
    assert result["idf1"] == 0
    assert result["false_positives"] == 2 and result["false_negatives"] == 1
