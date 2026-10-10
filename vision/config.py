"""Validated experiment settings; changing a setting creates a new experiment."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: Literal[1] = 1
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,80}$")
    model_asset_id: str
    video_asset_id: str
    device: str = Field(default="cpu", pattern=r"^(cpu|cuda:[0-9]+)$")
    image_size: int = Field(default=640, ge=160, le=1920, multiple_of=32)
    confidence: float = Field(default=0.25, gt=0, le=1)
    iou: float = Field(default=0.7, gt=0, le=1)
    max_detections: int = Field(default=300, ge=1, le=1000)
    tracker: Literal["none", "bytetrack", "botsort"] = "none"
    seed: int = Field(default=0, ge=0)


def resolve_person_class(names: dict[int, str]) -> int:
    """Resolve an unambiguous person label from inspected model metadata."""
    matches = [index for index, name in names.items() if name.strip().casefold() == "person"]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one person class, found {len(matches)}")
    return matches[0]
