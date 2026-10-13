"""End-to-end scoring on synthetic contract fixtures, never accuracy evidence."""

import json

import pytest

pytest.importorskip("motmetrics")

from conftest import get_records, refreeze, save_records, write_json

from vision.cli import main
from vision.evaluation.run import evaluate_person
from vision.provenance import sha256_file


def evaluate(bundle, tracking=None):
    return evaluate_person(
        bundle["reference"],
        bundle["images"],
        bundle["video"],
        bundle["baseline"],
        tracking or [bundle["bytetrack"], bundle["botsort"]],
        bundle["config"],
        bundle["output"],
    )


def test_perfect_comparison_reports_hashes_and_repeatable_metrics(evaluation_source):
    b = evaluation_source
    result = evaluate(b)
    assert result["detection"]["true_positives"] == 3
    assert result["detection"]["f1"] == 1
    for kind in ("bytetrack", "botsort"):
        assert result["tracking"][kind]["idf1"] == 1
        assert result["tracking"][kind]["mota"] == 1
    for name, digest in result["output_hashes"].items():
        assert sha256_file(b["output"] / name) == digest
    evidence = [
        json.loads(line) for line in (b["output"] / "frames.jsonl").read_text().splitlines()
    ]
    assert [r["frame_index"] for r in evidence] == [0, 1, 2]
    assert "not compute mAP" in (b["output"] / "report.md").read_text()
    old = (b["output"] / "comparison.json").read_bytes()
    with pytest.raises(FileExistsError):
        evaluate(b)
    assert (b["output"] / "comparison.json").read_bytes() == old
    first = b["output"]
    b["output"] = b["root"] / "repeat"
    second = evaluate(b, tracking=[b["botsort"], b["bytetrack"]])
    assert second == result
    assert (first / "frames.jsonl").read_bytes() == (b["output"] / "frames.jsonl").read_bytes()


def test_switch_and_fragmentation_comparison(evaluation_source):
    b = evaluation_source
    by = get_records(b, "bytetrack")
    by[1]["tracks"][0]["track_id"] = by[2]["tracks"][0]["track_id"] = 12
    save_records(b, "bytetrack", by)
    bo = get_records(b, "botsort")
    bo[1]["tracks"] = []
    save_records(b, "botsort", bo)
    result = evaluate(b)
    assert result["tracking"]["bytetrack"]["num_switches"] == 1
    assert result["tracking"]["bytetrack"]["idf1"] == pytest.approx(2 / 3)
    assert result["tracking"]["botsort"]["num_fragmentations"] == 1
    assert result["tracking"]["botsort"]["idf1"] == pytest.approx(0.8)
    evidence = [
        json.loads(line) for line in (b["output"] / "frames.jsonl").read_text().splitlines()
    ]
    assert evidence[1]["tracking"]["bytetrack"]["identity_switches"][0]["previous_track_id"] == 11


def test_selected_interval_starts_fresh_but_validates_whole_stream(evaluation_source):
    b = evaluation_source
    doc = json.loads(b["draft"].read_bytes())
    doc["review_start"] = doc["review_end"] = 1
    for i in (0, 2):
        doc["frames"][i].update(reviewed=False, reviewed_by=None)
    refreeze(b, doc)
    records = get_records(b, "bytetrack")
    records[1]["tracks"][0]["track_id"] = 12
    save_records(b, "bytetrack", records)
    result = evaluate(b)
    assert result["evaluated_frames"] == 1 and result["full_video_frames_validated"] == 3
    assert result["tracking"]["bytetrack"]["num_switches"] == 0
    assert result["tracking"]["bytetrack"]["idf1"] == 1
    b["output"] = b["root"] / "bad-outside-interval"
    records[2]["tracks"][0]["confidence"] = 0.5
    save_records(b, "bytetrack", records)
    with pytest.raises(ValueError, match="differs from source"):
        evaluate(b)
    assert not b["output"].exists()


def test_ignored_boxes_and_zero_area_clipped_track(evaluation_source):
    b = evaluation_source
    doc = json.loads(b["draft"].read_bytes())
    for frame in doc["frames"]:
        frame["people"][0].update(ignore=True, notes="Software fixture: unresolved identity")
    refreeze(b, doc)
    by = get_records(b, "bytetrack")
    by[0]["tracks"][0]["xyxy"] = [110, 10, 120, 70]
    save_records(b, "bytetrack", by)
    result = evaluate(b)
    assert result["ignored_reference_boxes"] == 3
    assert result["detection"]["excluded_predictions"] == 3
    assert result["tracking"]["bytetrack"]["false_positives"] == 1
    assert result["tracking"]["bytetrack"]["excluded_predictions"] == 2
    assert result["tracking"]["bytetrack"]["idf1"] is None
    assert result["tracking"]["botsort"]["mota"] is None
    assert "NaN" not in (b["output"] / "comparison.json").read_text()


def test_confidence_filter_applies_only_to_detector(evaluation_source):
    b = evaluation_source
    config = json.loads(b["config"].read_bytes())
    config["min_detection_confidence"] = 0.95
    write_json(b["config"], config)
    result = evaluate(b)
    assert result["detection"]["confidence_filtered_predictions"] == 3
    assert result["detection"]["false_negatives"] == 3
    assert result["detection"]["precision"] is None
    assert result["tracking"]["bytetrack"]["recall"] == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_video_sha256", "f" * 64),
        ("source_detections_sha256", "f" * 64),
        ("source_baseline_summary_sha256", "f" * 64),
        ("source_model", {}),
        ("source_detector_parameters", {"conf": 0.1}),
        ("fps", 30.0),
        ("frame_count", 2),
        ("person_class_id", 0),
    ],
)
def test_incompatible_tracker_rejected_before_output(evaluation_source, key, value):
    b = evaluation_source
    path = b["botsort"] / "summary.json"
    summary = json.loads(path.read_bytes())
    summary[key] = value
    write_json(path, summary)
    with pytest.raises(ValueError, match="mismatch"):
        evaluate(b)
    assert not b["output"].exists()


def test_requires_both_tracker_types(evaluation_source):
    b = evaluation_source
    with pytest.raises(ValueError, match="one ByteTrack"):
        evaluate(b, tracking=[b["bytetrack"], b["bytetrack"]])
    assert not b["output"].exists()


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r[0]["tracks"].append(r[0]["tracks"][0]), "duplicate"),
        (lambda r: r[0]["tracks"][0].update(detection_index=1), "differs from source"),
        (lambda r: r[0]["tracks"][0].update(confidence=0.5), "differs from source"),
        (lambda r: r[0]["tracks"][0].update(class_id=0), "class or detection index"),
        (lambda r: r[0].update(person_detection_count=2), "count mismatch"),
        (lambda r: r[0]["tracks"][0].update(track_id=2**53), "less than or equal"),
        (lambda r: r[0]["tracks"][0].update(xyxy=[20, 10, 10, 70]), "geometry"),
    ],
)
def test_invalid_track_records_leave_no_published_result(evaluation_source, mutation, match):
    b = evaluation_source
    records = get_records(b, "botsort")
    mutation(records)
    save_records(b, "botsort", records)
    with pytest.raises(ValueError, match=match):
        evaluate(b)
    assert not b["output"].exists()
    assert not list(b["root"].glob(".worksite-eval-*"))


def test_changed_stream_hash_rejects_after_parsing_without_publishing(evaluation_source):
    b = evaluation_source
    path = b["botsort"] / "tracks.jsonl"
    path.write_text(path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError):
        evaluate(b)
    assert not b["output"].exists()


def test_changed_video_and_reference_rejected(evaluation_source):
    b = evaluation_source
    b["video"].write_bytes(b"changed software fixture")
    with pytest.raises(ValueError, match="video differs"):
        evaluate(b)
    assert not b["output"].exists()


def test_cli_full_evaluation(evaluation_source, capsys):
    b = evaluation_source
    code = main(
        [
            "evaluate-person",
            "--reference",
            str(b["reference"]),
            "--images",
            str(b["images"]),
            "--video",
            str(b["video"]),
            "--baseline",
            str(b["baseline"]),
            "--tracking",
            str(b["bytetrack"]),
            str(b["botsort"]),
            "--config",
            str(b["config"]),
            "--output",
            str(b["output"]),
        ]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
