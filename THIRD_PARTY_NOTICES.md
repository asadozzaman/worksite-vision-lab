# Third-party notices

Research snapshot: 2026-10-10. Original Worksite Vision Lab code is AGPL-3.0-only.
That license does not relicense external content. No checkpoint, video or dataset
is included in the source repository.

| Component / asset | License evidence | Treatment |
|---|---|---|
| Ultralytics 8.4.173 and official models | [Ultralytics licensing](https://www.ultralytics.com/license), [source license](https://github.com/ultralytics/ultralytics/blob/main/LICENSE) | AGPL-3.0 open-source path; retain notices and meet applicable source-sharing requirements. Enterprise licensing is separate. |
| SiteGuard application | [MIT license](https://github.com/C-Nekopedia/SiteGuard/blob/main/LICENSE) | Inspected as research; application source is not copied. |
| SiteGuard `yolo26n_ppe.pt` | Repository MIT plus claimed Ultralytics training lineage; no independently established weight-specific permission | Quarantined for verification. No redistribution; do not infer a blanket MIT grant for data/weights. |
| Construction-PPE data | [Official dataset documentation](https://docs.ultralytics.com/datasets/detect/construction-ppe/) identifies AGPL-3.0 | Not acquired; per-image provenance and splits still require inspection. |
| Pexels candidate clips | [License](https://www.pexels.com/license/), [terms](https://www.pexels.com/terms-of-service/) | Separate acquisition; no raw redistribution. Credit creators in any approved demo; avoid unsupported negative portrayal or endorsement. |
| PyTorch / torchvision | [PyTorch license](https://github.com/pytorch/pytorch/blob/main/LICENSE), [torchvision license](https://github.com/pytorch/vision/blob/main/LICENSE) | BSD-style upstream licenses and bundled notices apply. |
| NumPy | [License](https://github.com/numpy/numpy/blob/main/LICENSE.txt) | BSD-3-Clause and bundled notices. |
| OpenCV Python | [Packaging license](https://github.com/opencv/opencv-python/blob/master/LICENSE.txt), upstream OpenCV/bundled library notices | Keep package notices; wheel bundles have separate licenses. |
| Pydantic | [License](https://github.com/pydantic/pydantic/blob/main/LICENSE) | MIT. |
| pytest / Ruff / Hatchling | Respective installed distribution license metadata | Development/build tools; retain their distribution licenses. |
| FFmpeg | [Legal information](https://ffmpeg.org/legal.html) | Invoked as a separately installed executable; exact build options affect LGPL/GPL obligations. Not bundled. |

This file tracks reviewed sources and unresolved permissions. A public download or
repository license is not proof of rights to every included asset. Consult
[assets.json](docs/assets.json) for asset-specific status and checksums.
