"""Synthetic reference records test software gates, never annotation accuracy."""

import hashlib
import json
from pathlib import Path

import pytest

from vision.cli import main
from vision.evaluation.reference import (
    PersonReference,
    empty_reference,
    freeze_reference,
    reference_status,
    validate_reference,
)
from vision.evaluation.render import render_editor


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def source(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    hashes = {}
    for index in range(2):
        name = f"{index:06d}.jpg"
        # Hash verification fixtures, not real JPEGs or evaluation images.
        payload = f"software test frame {index}".encode()
        (images / name).write_bytes(payload)
        hashes[name] = digest(payload)
    manifest = {
        "video_sha256": "a" * 64,
        "split": "development",
        "width": 100,
        "height": 200,
        "fps": 25.0,
        "frame_count": 2,
        "image_sha256": hashes,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    doc = empty_reference(manifest, digest(manifest_path.read_bytes())).model_dump(mode="json")
    return doc, manifest_path, images


def reviewed(doc):
    doc["reviewer"] = "Synthetic test reviewer"
    doc["review_end"] = 0
    doc["frames"][0].update(reviewed=True, reviewed_by=doc["reviewer"], empty_confirmed=True)
    doc.update(complete=True, human_attested=True, revision=1)
    doc["history"] = [
        {"revision": 1, "at": "2026-10-12T00:00:00Z", "action": "test_fixture", "frame_index": 0}
    ]
    return doc


def write_doc(doc, manifest_path):
    path = manifest_path.with_name("draft.json")
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def person(person_id="p001"):
    return {
        "person_id": person_id,
        "xyxy": [10.0, 20.0, 30.0, 80.0],
        "visibility": "visible",
        "truncated": False,
        "ignore": False,
        "notes": "",
    }


def test_empty_template_is_valid_but_not_ready(source):
    doc, manifest, _ = source
    result, _ = validate_reference(write_doc(doc, manifest), manifest)
    assert reference_status(result) == {
        "valid": True,
        "scope": "person_tracking",
        "split": "development",
        "reviewed_frames": 0,
        "selected_frames": 2,
        "person_boxes": 0,
        "ignored_boxes": 0,
        "complete": False,
        "human_attested": False,
        "ready_to_freeze": False,
        "accuracy_measured": False,
    }


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda d: d.update(complete=True), "complete flag"),
        (lambda d: d.update(human_attested=True), "human attestation"),
        (lambda d: d.update(review_end=2), "interval"),
        (lambda d: d.update(revision=1), "revision history"),
        (lambda d: d["frames"].reverse(), "contiguous"),
        (lambda d: d["frames"][0].update(reviewed_by="someone"), "must not claim"),
        (lambda d: d.update(annotation_version=" "), "must not be blank"),
    ],
)
def test_invalid_draft_states(source, mutation, match):
    doc, _, _ = source
    mutation(doc)
    with pytest.raises(ValueError, match=match):
        PersonReference.model_validate(doc)


def test_empty_frame_requires_confirmation(source):
    doc, _, _ = source
    reviewed(doc)["frames"][0]["empty_confirmed"] = False
    with pytest.raises(ValueError, match="explicit confirmation"):
        PersonReference.model_validate(doc)


@pytest.mark.parametrize(
    "box,identities,match",
    [
        (person("p002"), [{"person_id": "p001"}], "unknown manual identity"),
        ({**person(), "xyxy": [30, 20, 10, 80]}, [{"person_id": "p001"}], "invalid or out"),
        ({**person(), "xyxy": [-1, 20, 30, 80]}, [{"person_id": "p001"}], "invalid or out"),
        ({**person(), "xyxy": [10, 20, 101, 80]}, [{"person_id": "p001"}], "invalid or out"),
        ({**person(), "xyxy": [10, 20, float("nan"), 80]}, [{"person_id": "p001"}], "finite"),
    ],
)
def test_invalid_boxes(source, box, identities, match):
    doc, _, _ = source
    doc["identities"] = identities
    doc["frames"][0]["people"] = [box]
    with pytest.raises(ValueError, match=match):
        PersonReference.model_validate(doc)


def test_duplicate_identity_and_unresolved_review(source):
    doc, _, _ = source
    reviewed(doc)
    doc["identities"] = [{"person_id": "p001"}]
    frame = doc["frames"][0]
    frame.update(empty_confirmed=False, people=[person(), person()])
    with pytest.raises(ValueError, match="multiple boxes"):
        PersonReference.model_validate(doc)
    frame["people"] = [person(None)]
    with pytest.raises(ValueError, match="resolve identity"):
        PersonReference.model_validate(doc)
    frame["people"][0].update(ignore=True, visibility="uncertain")
    with pytest.raises(ValueError, match="resolve identity"):
        PersonReference.model_validate(doc)
    frame["people"][0]["notes"] = "Fixture: identity unresolved behind obstruction"
    assert PersonReference.model_validate(doc).complete


def test_source_binding_and_extra_fields(source):
    doc, manifest, _ = source
    doc["video_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="video_sha256 differs"):
        validate_reference(write_doc(doc, manifest), manifest)
    doc["manifest_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="different manifest"):
        validate_reference(write_doc(doc, manifest), manifest)
    doc["ppe"] = []
    with pytest.raises(ValueError, match="Extra inputs"):
        PersonReference.model_validate(doc)


@pytest.mark.parametrize("kind", ["human", "assistant", "software_fixture"])
def test_freeze_requires_explicit_human_attestation(source, kind):
    doc, manifest, images = source
    reviewed(doc).update(reviewer_kind=kind, human_attested=False)
    with pytest.raises(ValueError, match="explicit human attestation"):
        freeze_reference(write_doc(doc, manifest), manifest, images, manifest.parent / "frozen")
    if kind != "human":
        doc["human_attested"] = True
        with pytest.raises(ValueError, match="completed human review"):
            PersonReference.model_validate(doc)


def test_freeze_exact_bytes_selected_interval_and_no_overwrite(source):
    doc, manifest, images = source
    path = write_doc(reviewed(doc), manifest)
    output = manifest.parent / "frozen"
    record = freeze_reference(path, manifest, images, output)
    assert record["review_interval"] == [0, 0]
    assert record["reviewed_frames"] == 1
    assert not record["accuracy_measured"]
    assert record["annotation_sha256"] == digest(path.read_bytes())
    assert (output / "reference.json").read_bytes() == path.read_bytes()
    assert (output / "manifest.json").read_bytes() == manifest.read_bytes()
    with pytest.raises(FileExistsError):
        freeze_reference(path, manifest, images, output)


def test_freeze_rejects_changed_or_missing_images(source):
    doc, manifest, images = source
    path = write_doc(reviewed(doc), manifest)
    image = images / "000001.jpg"
    image.write_bytes(b"changed fixture")
    output = manifest.parent / "frozen"
    with pytest.raises(ValueError, match="review image changed"):
        freeze_reference(path, manifest, images, output)
    assert not output.exists()
    image.unlink()
    with pytest.raises(FileNotFoundError):
        freeze_reference(path, manifest, images, output)


def test_cli_reports_draft_and_refuses_freeze(source, capsys):
    doc, manifest, images = source
    path = write_doc(doc, manifest)
    assert main(["validate-reference", str(path), "--manifest", str(manifest)]) == 0
    assert json.loads(capsys.readouterr().out)["ready_to_freeze"] is False
    assert (
        main(
            [
                "freeze-reference",
                str(path),
                "--manifest",
                str(manifest),
                "--images",
                str(images),
                "--output",
                str(manifest.parent / "frozen"),
            ]
        )
        == 2
    )
    assert "explicit human attestation" in capsys.readouterr().err


def test_shared_browser_fixture_matches_python_schema():
    path = Path(__file__).parent / "fixtures/person-reference-v2.json"
    reference = PersonReference.model_validate_json(path.read_bytes())
    assert reference.reviewer_kind == "software_fixture"
    assert not reference.complete


def test_render_keeps_attribution_as_data_and_embeds_editor(source):
    doc, _, _ = source
    html = render_editor({"attribution": "</script><b>/*REFERENCE*/</b>"}, doc)
    assert html.count("</script>") == 3
    assert r"\u003c/script>\u003cb>/*REFERENCE*/\u003c/b>" in html
    assert "const initialReference={" in html
    assert "/*ANNOTATION_UI*/" not in html
    assert "/*ANNOTATION_CORE*/" not in html


def test_freeze_rejects_unexpected_image_paths(source):
    doc, manifest, images = source
    raw = json.loads(manifest.read_bytes())
    raw["image_sha256"]["../outside.jpg"] = raw["image_sha256"].pop("000001.jpg")
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    doc["manifest_sha256"] = digest(manifest.read_bytes())
    path = write_doc(reviewed(doc), manifest)
    with pytest.raises(ValueError, match="unexpected paths"):
        freeze_reference(path, manifest, images, manifest.parent / "frozen")
