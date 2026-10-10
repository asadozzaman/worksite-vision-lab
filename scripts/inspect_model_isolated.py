"""Run ONLY in the restricted container documented in docs/MODEL_RESEARCH.md.

The explicit allowlist applies to the inspected SiteGuard artifact, not arbitrary
checkpoints. No automatic import, automatic allowlisting, or unrestricted fallback.
"""

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import torch
import ultralytics
from torch import nn
from ultralytics import YOLO
from ultralytics.nn.modules.block import (
    C2PSA,
    SPPF,
    Attention,
    Bottleneck,
    C3k,
    C3k2,
    PSABlock,
)
from ultralytics.nn.modules.conv import Concat, Conv, DWConv
from ultralytics.nn.modules.head import Detect
from ultralytics.nn.tasks import DetectionModel

EXPECTED_SHA256 = "b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3"
ALLOWED = [
    DetectionModel,
    nn.Sequential,
    nn.ModuleList,
    Conv,
    DWConv,
    nn.Conv2d,
    nn.BatchNorm2d,
    nn.SiLU,
    C3k2,
    C3k,
    Bottleneck,
    SPPF,
    nn.MaxPool2d,
    C2PSA,
    PSABlock,
    Attention,
    nn.Upsample,
    Concat,
    Detect,
    nn.Identity,
]


def main() -> None:
    path = Path("/input/model.pt")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if checksum != EXPECTED_SHA256:
        raise ValueError("unreviewed checkpoint checksum; stop and inspect statically first")
    torch.set_num_threads(2)
    with torch.serialization.safe_globals(ALLOWED):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = checkpoint["model"].float().eval()
    if not isinstance(model, DetectionModel):
        raise ValueError("checkpoint does not contain a DetectionModel")
    # Build a new model from the installed package's official YOLO26 nano config.
    # Exact state-dict shape/key parity tests architecture, beyond the filename.
    root = Path(ultralytics.__file__).parent
    fresh = DetectionModel(
        str(root / "cfg/models/26/yolo26n.yaml"), nc=len(model.names), verbose=False
    )
    fresh.load_state_dict(model.state_dict(), strict=True)
    fresh.names = model.names
    fresh.eval()
    predictor = YOLO(str(root / "cfg/models/26/yolo26n.yaml"), task="detect", verbose=False)
    predictor.model = fresh
    predictions = predictor.predict(
        np.zeros((320, 320, 3), dtype=np.uint8),
        imgsz=320,
        device="cpu",
        conf=0.25,
        verbose=False,
        save=False,
    )
    report = {
        "schema_version": 1,
        "sha256": checksum,
        "size_bytes": path.stat().st_size,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "load_mode": "weights_only=True with explicit reviewed classes",
        "model_type": type(model).__name__,
        "names": model.names,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "head_type": type(model.model[-1]).__name__,
        "end2end": getattr(model.model[-1], "end2end", None),
        "reg_max": getattr(model.model[-1], "reg_max", None),
        "official_yolo26n_state_dict_strict_match": True,
        "checkpoint_ultralytics_version": checkpoint.get("version"),
        "checkpoint_date_unverified": checkpoint.get("date"),
        "checkpoint_license_claim_unverified": checkpoint.get("license"),
        "checkpoint_metrics_unverified": checkpoint.get("train_metrics"),
        "smoke_input": "synthetic black 320x320 image; compatibility only, NOT evaluation",
        "smoke_result_count": len(predictions),
        "smoke_box_count": len(predictions[0].boxes),
        "accuracy_reproduced": False,
        "real_video_inference_performed": False,
        "trackers_present": {
            name: (root / f"cfg/trackers/{name}.yaml").is_file()
            for name in ("bytetrack", "botsort")
        },
    }
    print("REPORT_JSON_BEGIN")
    print(json.dumps(report, indent=2))
    print("REPORT_JSON_END")


if __name__ == "__main__":
    main()
