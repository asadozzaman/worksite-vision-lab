import json
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
