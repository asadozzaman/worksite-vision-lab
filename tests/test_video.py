import json
import shutil
import subprocess

import pytest

from vision.video import probe_video


def test_probe_uses_argument_list_and_marks_content_unreviewed(tmp_path, monkeypatch):
    video = tmp_path / "clip with spaces.mp4"
    video.write_bytes(b"test fixture, not evaluation footage")
    monkeypatch.setattr("vision.video.shutil.which", lambda _: "ffprobe")

    def run(args, **kwargs):
        assert isinstance(args, list)
        assert args[-1] == str(video.resolve())
        assert args[args.index("-protocol_whitelist") + 1] == "file,pipe"
        assert not kwargs.get("shell", False)
        return subprocess.CompletedProcess(args, 0, json.dumps({"streams": [{"width": 640}]}))

    monkeypatch.setattr("vision.video.subprocess.run", run)
    report = probe_video(video)
    assert report["content_reviewed"] is False
    assert report["violations_verified"] is False
    assert report["ffprobe"]["streams"][0]["width"] == 640


def test_missing_ffprobe_is_actionable(tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.touch()
    monkeypatch.setattr("vision.video.shutil.which", lambda _: None)
    with pytest.raises(ValueError, match="install FFmpeg"):
        probe_video(video)


def test_audio_only_file_is_rejected(tmp_path, monkeypatch):
    video = tmp_path / "audio.mp4"
    video.touch()
    monkeypatch.setattr("vision.video.shutil.which", lambda _: "ffprobe")
    monkeypatch.setattr(
        "vision.video.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0, '{"streams": []}'),
    )
    with pytest.raises(ValueError, match="no video stream"):
        probe_video(video)


@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="FFmpeg is optional"
)
def test_real_ffprobe_on_synthetic_software_fixture(tmp_path):
    """Verify media tooling only; this is explicitly not evaluation footage."""
    video = tmp_path / "synthetic-software-test.mp4"
    subprocess.run(
        [
            shutil.which("ffmpeg"),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x48:r=5:d=1",
            "-c:v",
            "mpeg4",
            str(video),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    report = probe_video(video)
    stream = report["ffprobe"]["streams"][0]
    assert (stream["width"], stream["height"]) == (64, 48)
    assert stream["avg_frame_rate"] == "5/1"
    assert int(stream["nb_frames"]) == 5
    assert report["content_reviewed"] is False
