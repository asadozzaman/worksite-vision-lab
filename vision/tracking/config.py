"""Explicit tracker settings, independent of changing upstream defaults."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrackerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    tracker_type: Literal["bytetrack", "botsort"]
    track_high_thresh: float = Field(default=0.25, gt=0, le=1)
    track_low_thresh: float = Field(default=0.1, ge=0, lt=1)
    new_track_thresh: float = Field(default=0.25, gt=0, le=1)
    track_buffer: int = Field(default=30, ge=1, le=300)
    match_thresh: float = Field(default=0.8, gt=0, le=1)
    fuse_score: bool = True
    gmc_method: Literal["sparseOptFlow", "none"] = "sparseOptFlow"
    proximity_thresh: float = Field(default=0.5, ge=0, le=1)
    appearance_thresh: float = Field(default=0.8, ge=0, le=1)
    with_reid: Literal[False] = False
    model: Literal["auto"] = "auto"

    @model_validator(mode="after")
    def thresholds(self):
        if self.track_low_thresh >= self.track_high_thresh:
            raise ValueError("low threshold must be below high threshold")
        if self.new_track_thresh < self.track_high_thresh:
            raise ValueError("new track threshold must be at least high threshold")
        return self
