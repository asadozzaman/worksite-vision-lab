"""Create one versioned CFR analysis input; retain source and exact command."""

import argparse
import json
import subprocess
from pathlib import Path

from vision.detection.run import file_hash


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--fps", type=int, default=25)
    args = p.parse_args()
    if not 1 <= args.fps <= 60:
        p.error("fps must be 1..60")
    if args.output.exists() or args.output.with_suffix(".json").exists():
        p.error("output or manifest already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_sha = file_hash(args.source)
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-xerror",
        "-i",
        str(args.source.resolve()),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        f"scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2,fps={args.fps}",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-n",
        str(args.output.resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_frames",
        "-show_entries",
        "stream=width,height,avg_frame_rate,nb_read_frames",
        "-of",
        "json",
        str(args.output),
    ]
    probe = json.loads(subprocess.check_output(probe_cmd, text=True))["streams"][0]
    fps_n, fps_d = map(int, probe["avg_frame_rate"].split("/"))
    metadata = {
        "source_filename": args.source.name,
        "source_sha256": source_sha,
        "output_sha256": file_hash(args.output),
        "command": cmd,
        "stderr": result.stderr,
        "fps": fps_n / fps_d,
        "frame_count": int(probe["nb_read_frames"]),
        "width": probe["width"],
        "height": probe["height"],
        "timestamp_definition": "zero-based frame index divided by normalized CFR fps",
        "ffmpeg_version": subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[
            0
        ],
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
