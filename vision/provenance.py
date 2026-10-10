"""Content identity and explicit asset provenance; no implicit download or approval."""

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,80}$")
    kind: Literal["checkpoint", "video", "dataset"]
    source_url: HttpUrl
    revision: str | None = None
    creator: str | None = None
    license_url: HttpUrl | None = None
    license_status: Literal["unresolved", "source_terms_reviewed", "verified"]
    redistribution: Literal["not_authorized", "verified"] = "not_authorized"
    acquisition_status: Literal["candidate", "quarantined", "acquired", "validated"]
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    size_bytes: int | None = Field(default=None, gt=0)
    notes: str

    @model_validator(mode="after")
    def check_evidence(self) -> "Asset":
        if self.acquisition_status != "candidate" and not (self.sha256 and self.size_bytes):
            raise ValueError("acquired assets require a checksum and byte count")
        if self.license_status != "unresolved" and self.license_url is None:
            raise ValueError("reviewed licenses require a source URL")
        if self.redistribution == "verified" and self.license_status != "verified":
            raise ValueError("redistribution requires verified licensing")
        if self.acquisition_status == "validated" and self.license_status != "verified":
            raise ValueError("validation requires verified licensing")
        return self


class AssetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    assets: list[Asset]

    @model_validator(mode="after")
    def unique_ids(self) -> "AssetManifest":
        ids = [asset.id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("asset IDs must be unique")
        return self
