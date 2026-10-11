"""Synthetic software fixtures only; never used as research evaluation footage."""

import json

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("ultralytics")
pytest.importorskip("lap")

from vision.tracking.adapter import PersonTracker  # noqa: E402
from vision.tracking.config import TrackerConfig  # noqa: E402
from vision.tracking.run import file_hash, main  # noqa: E402


def person(score=0.9):
    return {"xyxy": [20, 10, 70, 90], "confidence": score, "class_id": 6}


@pytest.mark.parametrize("kind", ["bytetrack", "botsort"])
def test_empty_frames_advance_loss_and_short_gap_reacquires(kind):
    config = TrackerConfig(tracker_type=kind, gmc_method="none", track_buffer=3)
    tracker = PersonTracker(config, 6, 100, 100)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    first, _ = tracker.update([person()], frame)
    assert len(first) == 1
    assert tracker.update([], frame) == ([], 0)
    recovered, _ = tracker.update([person()], frame)
    assert recovered[0]["track_id"] == first[0]["track_id"]
    for _ in range(6):
        tracker.update([], frame)
    tracker.update([person()], frame)  # new track requires confirmation after first frame
    replacement, _ = tracker.update([person()], frame)
    assert replacement[0]["track_id"] != first[0]["track_id"]
    assert tracker.tracker.frame_id == 11


@pytest.mark.parametrize("kind", ["bytetrack", "botsort"])
def test_ppe_filtered_original_index_retained_and_low_score_recovers(kind):
    tracker = PersonTracker(TrackerConfig(tracker_type=kind, gmc_method="none"), 6, 100, 100)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    helmet = {"xyxy": [25, 10, 40, 25], "confidence": 0.99, "class_id": 0}
    first, count = tracker.update([helmet, person()], frame)
    assert count == 1
    assert first[0]["class_id"] == 6
    assert first[0]["detection_index"] == 1
    recovered, _ = tracker.update([helmet, person(0.15)], frame)
    assert recovered[0]["track_id"] == first[0]["track_id"]
    assert recovered[0]["confidence"] == pytest.approx(0.15)


@pytest.fixture
def replay_input(tmp_path):
    import cv2

    video = tmp_path / "fixture.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 25, (100, 100))
    assert writer.isOpened()
    for _ in range(3):
        writer.write(np.zeros((100, 100, 3), dtype=np.uint8))
    writer.release()
    records = [
        {
            "frame_index": i,
            "timestamp_seconds": i / 25,
            "width": 100,
            "height": 100,
            "detections": [{**person(), "class_name": "Person"}] if i != 1 else [],
        }
        for i in range(3)
    ]
    detections = tmp_path / "detections.jsonl"
    detections.write_text("".join(json.dumps(r) + "\n" for r in records))
    summary = tmp_path / "baseline.json"
    summary.write_text(
        json.dumps(
            {
                "status": "completed",
                "model": {"names": {"6": "Person"}},
                "video_sha256": file_hash(video),
                "output_hashes": {"detections.jsonl": file_hash(detections)},
                "width": 100,
                "height": 100,
                "fps": 25,
                "frame_count": 3,
                "parameters": {"conf": 0.25},
            }
        )
    )
    config = tmp_path / "config.json"
    config.write_text(TrackerConfig(tracker_type="botsort", gmc_method="none").model_dump_json())
    output = tmp_path / "result"
    argv = [
        "--video",
        str(video),
        "--detections",
        str(detections),
        "--baseline-summary",
        str(summary),
        "--config",
        str(config),
        "--output",
        str(output),
    ]
    return argv, output, detections, summary


def test_replay_alignment_and_no_overwrite(replay_input):
    argv, output, _, _ = replay_input
    main(argv)
    records = [json.loads(line) for line in (output / "tracks.jsonl").read_text().splitlines()]
    assert [r["timestamp_seconds"] for r in records] == [0, 0.04, 0.08]
    assert records[1]["tracks"] == []
    assert records[0]["tracks"][0]["track_id"] == records[2]["tracks"][0]["track_id"]
    original_summary = (output / "summary.json").read_bytes()
    with pytest.raises(FileExistsError):
        main(argv)
    assert (output / "summary.json").read_bytes() == original_summary
    assert not (output / "failure.json").exists()


def test_corrupt_detection_checksum_rejected_before_output(replay_input):
    argv, output, detections, _ = replay_input
    detections.write_text("corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        main(argv)
    assert not output.exists()


def test_truncated_stream_records_failure_without_success(replay_input):
    argv, output, detections, summary = replay_input
    detections.write_text(detections.read_text().splitlines()[0] + "\n")
    meta = json.loads(summary.read_text())
    meta["output_hashes"]["detections.jsonl"] = file_hash(detections)
    summary.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="frame counts"):
        main(argv)
    assert json.loads((output / "failure.json").read_text())["status"] == "failed"
    assert not (output / "summary.json").exists()
