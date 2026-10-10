"""Read local video metadata with ffprobe; never accepts URLs or shell expressions."""

import json
import shutil
import subprocess
from pathlib import Path

from vision.provenance import sha256_file


def probe_video(path: Path) -> dict:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("video must be a local file")
    executable = shutil.which("ffprobe")
    if executable is None:
        raise ValueError("ffprobe is required; install FFmpeg and add it to PATH")
    result = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,duration:"
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise ValueError("ffprobe could not read the local video")
    metadata = json.loads(result.stdout)
    if not metadata.get("streams"):
        raise ValueError("file contains no video stream")
    return {
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "ffprobe": metadata,
        "content_reviewed": False,
        "violations_verified": False,
    }
