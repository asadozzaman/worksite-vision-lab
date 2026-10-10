import hashlib
import json
import pickle
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from vision.checkpoint import MAX_PICKLE_BYTES, inspect_checkpoint
from vision.cli import main
from vision.config import ExperimentConfig, resolve_person_class
from vision.provenance import Asset, AssetManifest, sha256_file


def write_archive(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            # ZipInfo normalizes Windows backslashes on construction. Assign after
            # construction to preserve adversarial archive bytes in this fixture.
            info = zipfile.ZipInfo("placeholder")
            info.filename = name
            archive.writestr(info, data)
    return path


def test_static_inspection_never_executes_pickle(tmp_path):
    marker = tmp_path / "executed"

    class Payload:
        def __reduce__(self):
            return eval, (f"__import__('pathlib').Path({str(marker)!r}).touch()",)

    path = write_archive(tmp_path / "test.pt", [("archive/data.pkl", pickle.dumps(Payload(), 2))])
    report = inspect_checkpoint(path)
    assert not marker.exists()
    assert report["load_performed"] is False
    assert "__builtin__.eval" in report["globals"]
    assert report["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", ["../data.pkl", "/data.pkl", "x\\data.pkl"])
def test_rejects_unsafe_member_names(tmp_path, name):
    path = write_archive(tmp_path / "unsafe.pt", [(name, pickle.dumps({}))])
    with pytest.raises(ValueError, match="unsafe archive"):
        inspect_checkpoint(path)


def test_rejects_duplicate_pickle(tmp_path):
    path = write_archive(tmp_path / "dupe.pt", [("a/data.pkl", b""), ("b/data.pkl", b"")])
    with pytest.raises(ValueError, match="exactly one"):
        inspect_checkpoint(path)


def test_rejects_large_compressed_pickle(tmp_path):
    path = write_archive(tmp_path / "big.pt", [("a/data.pkl", b"x" * (MAX_PICKLE_BYTES + 1))])
    with pytest.raises(ValueError, match="metadata exceeds"):
        inspect_checkpoint(path)


def test_rejects_non_zip(tmp_path):
    path = tmp_path / "not.pt"
    path.write_text("not a checkpoint")
    with pytest.raises(ValueError, match="ZIP"):
        inspect_checkpoint(path)


def test_dynamic_globals_are_flagged(tmp_path):
    path = write_archive(tmp_path / "dynamic.pt", [("data.pkl", pickle.dumps(Path("x"), 4))])
    assert inspect_checkpoint(path)["dynamic_globals"] > 0


def test_hash_streams_file(tmp_path):
    data = b"x" * (1024 * 1024 + 5)
    path = tmp_path / "data"
    path.write_bytes(data)
    assert sha256_file(path) == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", 0),
        ("confidence", 1.1),
        ("confidence", float("nan")),
        ("image_size", 641),
        ("tracker", "made-up"),
        ("device", "cuda"),
        ("typo_setting", 2),
    ],
)
def test_invalid_experiment_settings(field, value):
    settings = dict(name="baseline", model_asset_id="model", video_asset_id="video")
    settings[field] = value
    with pytest.raises(ValidationError):
        ExperimentConfig(**settings)


def test_person_class_uses_metadata():
    assert resolve_person_class({0: "helmet", 6: "Person"}) == 6
    assert resolve_person_class({0: "person", 1: "bicycle"}) == 0


@pytest.mark.parametrize("names", [{0: "helmet"}, {0: "person", 6: "Person"}])
def test_person_class_must_be_unambiguous(names):
    with pytest.raises(ValueError, match="exactly one"):
        resolve_person_class(names)


def candidate(**overrides):
    return (
        dict(
            id="test-video",
            kind="video",
            source_url="https://example.org/video",
            license_status="unresolved",
            acquisition_status="candidate",
            notes="test fixture",
        )
        | overrides
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"acquisition_status": "acquired"},
        {"redistribution": "verified"},
        {"license_status": "verified"},
        {"sha256": "wrong"},
        {"unexpected": "value"},
    ],
)
def test_provenance_cannot_silently_claim_verification(overrides):
    with pytest.raises(ValidationError):
        Asset(**candidate(**overrides))


def test_duplicate_assets_rejected():
    with pytest.raises(ValidationError, match="unique"):
        AssetManifest(reviewed_on="2026-10-10", assets=[candidate(), candidate()])


def test_cli_has_structured_errors(tmp_path, capsys):
    path = tmp_path / "invalid.json"
    path.write_text("{}")
    assert main(["validate-config", str(path)]) == 2
    assert "error" in json.loads(capsys.readouterr().err)


def test_doctor_does_not_expose_environment_variables(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret-not-real")
    assert main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "test-secret-not-real" not in output
    assert json.loads(output)["gpu_execution_verified"] is False


def test_repository_manifests():
    root = Path(__file__).resolve().parents[1]
    AssetManifest.model_validate_json((root / "docs/assets.json").read_text())
    ExperimentConfig.model_validate_json(
        (root / "experiments/configs/baseline-cpu.json").read_text()
    )
