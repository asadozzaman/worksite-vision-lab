"""Restricted loader for the one audited SiteGuard artifact; run in isolation."""

import hashlib
import platform
from pathlib import Path

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


def load_reviewed_model(path: Path):
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if checksum != EXPECTED_SHA256:
        raise ValueError("unreviewed checkpoint checksum")
    if ultralytics.__version__ != "8.4.173":
        raise ValueError("this loader is verified only with Ultralytics 8.4.173")
    with torch.serialization.safe_globals(ALLOWED):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("version") != "8.4.37":
        raise ValueError("unexpected producer version")
    original = checkpoint["model"].float().eval()
    if not isinstance(original, DetectionModel):
        raise ValueError("expected DetectionModel")
    # v8.4.37 Detect.end2end defaulted a missing _end2end to True.
    # v8.4.173 defaults it to False. Restore the producer's semantics explicitly.
    head = original.model[-1]
    mode = head.__dict__.get("_end2end", True)
    if not isinstance(mode, bool) or not hasattr(head, "one2one_cv2"):
        raise ValueError("unexpected detection head metadata")
    root = Path(ultralytics.__file__).parent
    fresh = DetectionModel(str(root / "cfg/models/26/yolo26n.yaml"), nc=11, verbose=False)
    fresh.load_state_dict(original.state_dict(), strict=True)
    fresh.names = original.names
    fresh.model[-1].end2end = mode
    fresh.eval()
    predictor = YOLO(str(root / "cfg/models/26/yolo26n.yaml"), task="detect", verbose=False)
    fresh.args = predictor.model.args.copy()
    fresh.task = "detect"
    predictor.model = fresh
    metadata = {
        "sha256": checksum,
        "size_bytes": path.stat().st_size,
        "names": original.names,
        "parameter_count": sum(p.numel() for p in original.parameters()),
        "producer_version": checkpoint["version"],
        "runtime_ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "effective_end2end": mode,
        "mode_reason": "restore v8.4.37 missing _end2end default True; explicit in v8.4.173",
        "official_yolo26n_state_dict_strict_match": True,
        "embedded_license": checkpoint.get("license"),
        "load_mode": "weights_only=True, explicit reviewed allowlist, checksum pinned",
    }
    return predictor, metadata
