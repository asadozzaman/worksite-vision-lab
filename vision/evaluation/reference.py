"""Person-reference schema, source binding and explicit human-review freeze gate."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vision.provenance import sha256_file

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
PersonId = Annotated[str, Field(pattern=r"^p[0-9]{3,6}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class PersonIdentity(StrictModel):
    person_id: PersonId
    notes: str = Field(default="", max_length=2000)


class PersonBox(StrictModel):
    person_id: PersonId | None = None
    xyxy: list[float] = Field(min_length=4, max_length=4)
    visibility: Literal["visible", "partial", "uncertain"] = "visible"
    truncated: bool = False
    ignore: bool = False
    notes: str = Field(default="", max_length=2000)


class ReferenceFrame(StrictModel):
    frame_index: int = Field(ge=0)
    reviewed: bool = False
    reviewed_by: str | None = Field(default=None, max_length=200)
    empty_confirmed: bool = False
    people: list[PersonBox] = Field(default_factory=list, max_length=1000)
    notes: str = Field(default="", max_length=4000)


class Revision(StrictModel):
    revision: int = Field(ge=1)
    at: str = Field(min_length=1, max_length=50)
    action: str = Field(min_length=1, max_length=100)
    frame_index: int | None = Field(default=None, ge=0)


class PersonReference(StrictModel):
    schema_version: Literal[2] = 2
    scope: Literal["person_tracking"] = "person_tracking"
    manifest_sha256: Digest
    video_sha256: Digest
    split: Literal["development", "test"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)
    frame_count: int = Field(gt=0, le=100000)
    review_start: int = Field(ge=0)
    review_end: int = Field(ge=0)
    reviewer: str = Field(default="", max_length=200)
    reviewer_kind: Literal["human", "assistant", "software_fixture"] = "human"
    annotation_version: str = Field(default="v1", min_length=1, max_length=100)
    human_attested: bool = False
    complete: bool = False
    revision: int = Field(default=0, ge=0, le=200000)
    identities: list[PersonIdentity] = Field(default_factory=list, max_length=10000)
    frames: list[ReferenceFrame] = Field(max_length=100000)
    history: list[Revision] = Field(default_factory=list, max_length=200000)

    @model_validator(mode="after")
    def consistent(self):
        if not self.annotation_version.strip():
            raise ValueError("annotation version must not be blank")
        if not 0 <= self.review_start <= self.review_end < self.frame_count:
            raise ValueError("review interval must be inside the clip")
        if len(self.frames) != self.frame_count:
            raise ValueError("reference must contain every frame, including unreviewed frames")
        ids = [i.person_id for i in self.identities]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate manual identity")
        for index, frame in enumerate(self.frames):
            if frame.frame_index != index:
                raise ValueError("frames must be contiguous and zero-based")
            used = []
            if frame.people and frame.empty_confirmed:
                raise ValueError(f"frame {index}: people conflict with no-people confirmation")
            if frame.reviewed:
                if not self.reviewer.strip() or frame.reviewed_by != self.reviewer:
                    raise ValueError(f"frame {index}: reviewer is missing or mismatched")
                if not frame.people and not frame.empty_confirmed:
                    raise ValueError(f"frame {index}: empty frame needs explicit confirmation")
            elif frame.reviewed_by is not None:
                raise ValueError(f"frame {index}: unreviewed frame must not claim a reviewer")
            for box in frame.people:
                x1, y1, x2, y2 = box.xyxy
                if not (0 <= x1 < x2 <= self.width and 0 <= y1 < y2 <= self.height):
                    raise ValueError(f"frame {index}: invalid or out-of-bounds box")
                if box.person_id is not None:
                    if box.person_id not in ids:
                        raise ValueError(f"frame {index}: unknown manual identity")
                    used.append(box.person_id)
                if frame.reviewed and (
                    (box.person_id is None and not box.ignore)
                    or (box.visibility == "uncertain" and not box.ignore)
                    or (box.ignore and not box.notes.strip())
                ):
                    raise ValueError(
                        f"frame {index}: resolve identity or record a reason to ignore"
                    )
            if len(set(used)) != len(used):
                raise ValueError(f"frame {index}: identity appears on multiple boxes")
        actual_complete = all(
            f.reviewed for f in self.frames[self.review_start : self.review_end + 1]
        )
        if self.complete != actual_complete:
            raise ValueError("complete flag disagrees with reviewed interval")
        if self.human_attested and (self.reviewer_kind != "human" or not self.complete):
            raise ValueError("human attestation requires completed human review")
        if [h.revision for h in self.history] != list(range(1, self.revision + 1)):
            raise ValueError("revision history must be contiguous and match revision")
        if any(
            h.frame_index is not None and h.frame_index >= self.frame_count for h in self.history
        ):
            raise ValueError("revision references a frame outside the clip")
        return self


def empty_reference(manifest, manifest_sha256):
    return PersonReference(
        manifest_sha256=manifest_sha256,
        video_sha256=manifest["video_sha256"],
        split=manifest["split"],
        width=manifest["width"],
        height=manifest["height"],
        fps=float(manifest["fps"]),
        frame_count=manifest["frame_count"],
        review_start=0,
        review_end=manifest["frame_count"] - 1,
        frames=[ReferenceFrame(frame_index=i) for i in range(manifest["frame_count"])],
    )


def _read_validated(path: Path, manifest_path: Path):
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("reference exceeds 50 MiB")
    annotation_bytes = path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    reference = PersonReference.model_validate_json(annotation_bytes)
    if reference.manifest_sha256 != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError("reference belongs to a different manifest")
    manifest = json.loads(manifest_bytes)
    required = {"video_sha256", "split", "width", "height", "fps", "frame_count", "image_sha256"}
    if not isinstance(manifest, dict) or not required.issubset(manifest):
        raise ValueError("source manifest is missing required fields")
    for key in ("video_sha256", "split", "width", "height", "fps", "frame_count"):
        if getattr(reference, key) != manifest[key]:
            raise ValueError(f"reference {key} differs from source manifest")
    return reference, manifest, annotation_bytes, manifest_bytes


def validate_reference(path: Path, manifest_path: Path):
    reference, manifest, _, _ = _read_validated(path, manifest_path)
    return reference, manifest


def reference_status(reference):
    selected = reference.frames[reference.review_start : reference.review_end + 1]
    return {
        "valid": True,
        "scope": reference.scope,
        "split": reference.split,
        "reviewed_frames": sum(f.reviewed for f in selected),
        "selected_frames": len(selected),
        "person_boxes": sum(len(f.people) for f in selected),
        "ignored_boxes": sum(b.ignore for f in selected for b in f.people),
        "complete": reference.complete,
        "human_attested": reference.human_attested,
        "ready_to_freeze": reference.complete
        and reference.human_attested
        and reference.revision > 0,
        "accuracy_measured": False,
    }


def freeze_reference(path: Path, manifest_path: Path, images: Path, output: Path):
    reference, manifest, annotation_bytes, manifest_bytes = _read_validated(path, manifest_path)
    if not reference.complete or not reference.human_attested or reference.reviewer_kind != "human":
        raise ValueError("freeze requires a complete interval and explicit human attestation")
    if not reference.reviewer.strip() or reference.revision == 0:
        raise ValueError("freeze requires reviewer identity and revision history")
    expected_names = {f"{i:06d}.jpg" for i in range(reference.frame_count)}
    if (
        not isinstance(manifest["image_sha256"], dict)
        or set(manifest["image_sha256"]) != expected_names
    ):
        raise ValueError("manifest image list is incomplete or contains unexpected paths")
    image_root = images.resolve(strict=True)
    for name, digest in manifest["image_sha256"].items():
        image_path = (image_root / name).resolve(strict=True)
        if image_path.parent != image_root or sha256_file(image_path) != digest:
            raise ValueError(f"review image changed: {name}")
    # Copy the exact submitted bytes; the output must be a new directory.
    record = {
        "schema_version": 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "annotation_sha256": hashlib.sha256(annotation_bytes).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "reviewer": reference.reviewer,
        "annotation_version": reference.annotation_version,
        "revision": reference.revision,
        "review_interval": [reference.review_start, reference.review_end],
        **reference_status(reference),
        "attestation_scope": (
            "reviewer declaration; software validation is not independent label QA"
        ),
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "reference.json").write_bytes(annotation_bytes)
    (output / "manifest.json").write_bytes(manifest_bytes)
    (output / "freeze.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record
