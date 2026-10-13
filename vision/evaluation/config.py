"""Explicit person-only evaluation protocol, distinct from detector/tracker settings."""

from typing import Literal

from pydantic import Field

from vision.evaluation.reference import StrictModel


class EvaluationConfig(StrictModel):
    schema_version: Literal[1] = 1
    scope: Literal["person_tracking"] = "person_tracking"
    match_iou: float = Field(default=0.5, gt=0, le=1)
    ignore_ioa: float = Field(default=0.5, gt=0, le=1)
    min_detection_confidence: float = Field(default=0.25, ge=0, le=1)
    detection_matching: Literal["maximum_cardinality_then_iou"] = "maximum_cardinality_then_iou"
    tracking_matching: Literal["motmetrics_continuity_then_assignment"] = (
        "motmetrics_continuity_then_assignment"
    )
    tracking_confidence: Literal["all_emitted"] = "all_emitted"
    track_geometry: Literal["clip_to_image_keep_zero_area"] = "clip_to_image_keep_zero_area"
    ignore_policy: Literal["ioa_without_eligible_valid_person"] = (
        "ioa_without_eligible_valid_person"
    )
    switch_gap: Literal["unlimited_within_interval"] = "unlimited_within_interval"

    def policy(self):
        return {
            **self.model_dump(mode="json"),
            "threshold_boundary": "inclusive: IoU >= match_iou and IoA >= ignore_ioa",
            "ioa_denominator": "prediction area after clipping; zero area gives zero IoA",
            "ignore_rule": (
                "remove a prediction only if IoA with an ignored box meets the threshold "
                "and IoU with every non-ignored person is below match_iou; many predictions "
                "can be excluded by one ignored box; duplicate eligible predictions remain FPs"
            ),
            "interval_state": "fresh identity accumulator at selected interval start",
            "undefined_ratios": "null; no-GT intervals have null identity ratios and MOTA",
            "benchmark_scope": "custom person-only protocol; not an official MOTChallenge score",
        }
