"""Compatibility smoke test. Run only in the documented restricted container."""

import json
from pathlib import Path

import numpy as np
import torch

from vision.detection.model import load_reviewed_model


def main():
    torch.set_num_threads(2)
    predictor, metadata = load_reviewed_model(Path("/input/model.pt"))
    result = predictor.predict(
        np.zeros((320, 320, 3), dtype=np.uint8),
        imgsz=320,
        device="cpu",
        conf=0.25,
        end2end=metadata["effective_end2end"],
        verbose=False,
        save=False,
    )
    metadata.update(
        {
            "smoke_input": "synthetic black 320x320 image; compatibility only",
            "smoke_result_count": len(result),
            "smoke_box_count": len(result[0].boxes),
            "accuracy_reproduced": False,
            "real_video_inference_performed": False,
        }
    )
    print("REPORT_JSON_BEGIN")
    print(json.dumps(metadata, indent=2))
    print("REPORT_JSON_END")


if __name__ == "__main__":
    main()
