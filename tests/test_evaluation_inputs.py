"""Input integrity gates without numerical or inference dependencies."""

import json

import pytest

from vision.cli import main
from vision.evaluation.config import EvaluationConfig
from vision.evaluation.reference import load_frozen_reference
from vision.evaluation.sources import (
    DetectionFrame,
    FrameStream,
    bind_baseline,
    output_digest,
    read_summary,
)


def test_frozen_reference_accepts_bound_fixture(evaluation_source):
    b = evaluation_source
    reference, _, hashes = load_frozen_reference(b["reference"], b["images"])
    assert reference.complete and reference.human_attested
    assert len(hashes["freeze_sha256"]) == 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("annotation_sha256", "0" * 64),
        ("manifest_sha256", "0" * 64),
        ("review_interval", [0, 0]),
        ("reviewer", "other"),
        ("reviewed_frames", 1),
        ("ready_to_freeze", False),
        ("frozen_at", "2026-10-12T00:00:00"),
    ],
)
def test_freeze_record_tampering_is_rejected(evaluation_source, field, value):
    b = evaluation_source
    path = b["reference"] / "freeze.json"
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        load_frozen_reference(b["reference"], b["images"])


def test_changed_images_and_nonhuman_reference_rejected(evaluation_source):
    b = evaluation_source
    (b["images"] / "000001.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError, match="review image changed"):
        load_frozen_reference(b["reference"], b["images"])
    path = b["reference"] / "reference.json"
    doc = json.loads(path.read_bytes())
    doc.update(reviewer_kind="assistant", human_attested=False)
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="human-attested"):
        load_frozen_reference(b["reference"], b["images"])


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r[0].update(frame_index=2), "contiguous"),
        (lambda r: r[0].update(timestamp_seconds=0.5), "timestamp"),
        (lambda r: r[0].update(width=99), "dimensions"),
        (lambda r: r[0].update(frame_index=True), "integer"),
        (lambda r: r.pop(), "truncated"),
        (lambda r: r.append(r[-1]), "extra frames"),
    ],
)
def test_prediction_stream_structure(evaluation_source, mutation, match):
    b = evaluation_source
    reference, _, _ = load_frozen_reference(b["reference"], b["images"])
    path = b["baseline"] / "detections.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    mutation(records)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        list(FrameStream(path, DetectionFrame, "0" * 64, reference))


def test_prediction_checksum_and_confidence_floor(evaluation_source):
    b = evaluation_source
    reference, _, _ = load_frozen_reference(b["reference"], b["images"])
    path = b["baseline"] / "detections.jsonl"
    with pytest.raises(ValueError, match="checksum"):
        list(FrameStream(path, DetectionFrame, "0" * 64, reference))
    summary, _ = read_summary(b["baseline"])
    with pytest.raises(ValueError, match="detector floor"):
        bind_baseline(summary, reference, EvaluationConfig(min_detection_confidence=0.1))


@pytest.mark.parametrize(
    "field,value",
    [("match_iou", 0), ("ignore_ioa", 1.1), ("min_detection_confidence", float("nan"))],
)
def test_invalid_protocol_is_rejected(field, value):
    with pytest.raises(ValueError):
        EvaluationConfig(**{field: value})


@pytest.mark.parametrize(
    "hashes", [[], {}, {"detections.jsonl": "not a checksum"}, {"detections.jsonl": "z" * 64}]
)
def test_malformed_output_hashes_are_rejected(hashes):
    with pytest.raises(ValueError, match="output_hashes|checksum"):
        output_digest({"output_hashes": hashes}, "detections.jsonl")


def test_cli_rejects_unfrozen_inputs_without_creating_output(evaluation_source, capsys):
    b = evaluation_source
    code = main(
        [
            "evaluate-person",
            "--reference",
            str(b["root"]),
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
    assert code == 2 and not b["output"].exists()
    assert json.loads(capsys.readouterr().err)["error"]
