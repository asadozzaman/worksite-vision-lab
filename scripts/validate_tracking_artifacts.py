"""Check saved tracking records, hashes and decoded video lengths without ground truth."""

import argparse
import json
import subprocess
from pathlib import Path

from vision.detection.run import file_hash
from vision.tracking.records import TrackObservations


def validate_run(folder):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if summary["status"] != "completed":
        raise ValueError(f"incomplete run: {folder}")
    for name in ("tracks.jsonl", "annotated.mp4"):
        if file_hash(folder / name) != summary["output_hashes"][name]:
            raise ValueError(f"output hash mismatch: {folder / name}")
    observations = TrackObservations()
    count = 0
    with (folder / "tracks.jsonl").open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            record = json.loads(line)
            if record["frame_index"] != index:
                raise ValueError("frame sequence mismatch")
            if abs(record["timestamp_seconds"] - index / summary["fps"]) > 1e-9:
                raise ValueError("timestamp mismatch")
            if any(t["class_id"] != summary["person_class_id"] for t in record["tracks"]):
                raise ValueError("non-person track")
            observations.update(record)
            count += 1
    if (
        count != summary["frame_count"]
        or observations.summary(summary["fps"]) != summary["observations"]
    ):
        raise ValueError("recomputed observations disagree with summary")
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames,width,height",
            "-of",
            "json",
            str(folder / "annotated.mp4"),
        ]
    )
    video = json.loads(output)["streams"][0]
    if int(video["nb_read_frames"]) != count:
        raise ValueError("annotated video frame count mismatch")
    if (video["width"], video["height"]) != (summary["width"], summary["height"]):
        raise ValueError("annotated video dimensions mismatch")
    return {"run": folder.name, "frames": count, "status": "validated"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([validate_run(folder) for folder in args.runs], indent=2))


if __name__ == "__main__":
    main()
