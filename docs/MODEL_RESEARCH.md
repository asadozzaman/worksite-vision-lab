# YOLO26 checkpoint investigation

Investigation date: 2026-10-10 (Asia/Dhaka). Distinguish upstream claims, static
evidence, isolated execution and reproduced video accuracy.

## Source and identity

The [SiteGuard repository](https://github.com/C-Nekopedia/SiteGuard) was created
2026-04-21. GitHub's path history identifies commit
`f4d1a097679439f3eaec4e5569d4e52d479cf592` (2026-04-23 19:48:54 UTC) as the commit
adding the candidate checkpoint. This is a publication observation, not an
independent training audit. No releases or training data were used locally.

- Path: `data/models/yolo26n_ppe.pt`.
- Git blob ID: `d462632cbb2b556b534e4243260240f7d5bff1e2`.
- Downloaded bytes: **5,394,437**.
- SHA-256: `b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`.
- Local location: ignored `data/quarantine/yolo26n_ppe.pt`.
- Static ZIP inspection: 718 entries, 185,046-byte pickle, 74,135 opcodes;
  28 explicit global references, no `STACK_GLOBAL` opcodes.
- [Static machine-readable evidence](evidence/checkpoint-static.json).

The upstream README claims YOLO26n, 11 classes, 50 training epochs, mAP50 0.523
and mAP50–95 0.270. These are **upstream claims, not our results**. Reproduction
would require the precise data version/splits, labels, training/validation settings
and an independent evaluation. No accuracy has been reproduced here.

## Dependencies and architecture

[Official YOLO26 documentation](https://docs.ultralytics.com/models/yolo26/) confirms
the architecture and `yolo26n.pt` naming. Local Ultralytics **8.4.173** contains
`cfg/models/26/yolo26.yaml`, ByteTrack and BoT-SORT configuration files. The model
configuration declares `end2end: True` and `reg_max: 1`. Do not rely on a renamed
file as architecture evidence: the isolated procedure checks exact state-dict keys
and tensor shapes against a fresh official YOLO26n model with the loaded class count.

The existing Windows installation reports Torch 2.7.0, torchvision 0.22.0,
NumPy 1.26.4 and OpenCV 4.11.0.86. The project does not alter that environment;
foundation dependencies live in `.venv`, model verification in Docker.
PyPI reported Ultralytics 8.4.175 as latest during research, but this project pins
8.4.173 to the version inspected rather than upgrading without evidence.

Tracking documentation specifies persistent state only for consecutive frames of
one stream ([source](https://docs.ultralytics.com/modes/track/)). ByteTrack and
BoT-SORT must receive only person detections; downstream association retains the
other PPE detections. Presence of tracker configuration files is not a tracking
experiment or a runtime benchmark.

## Security and isolated reproduction

Third-party `.pt` files may serialize executable objects. The static inspector
only parses bounded ZIP/pickle bytes and is not a malware certification tool.
[PyTorch's serialization guidance](https://docs.pytorch.org/docs/stable/notes/serialization.html)
explains restricted loading and its limits. Do not call unrestricted `torch.load`
or `YOLO(path)` on an untrusted third-party checkpoint on the host.

Build the disposable inspection image (downloads CPU libraries, no CUDA):

```powershell
docker build -f docker/checkpoint-inspector.Dockerfile -t worksite-checkpoint-inspector:8.4.173 .
$model = (Resolve-Path data/quarantine/yolo26n_ppe.pt).Path
$script = (Resolve-Path scripts/inspect_model_isolated.py).Path
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges `
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,noexec,nosuid,size=256m `
  --mount "type=bind,source=$model,target=/input/model.pt,readonly" `
  --mount "type=bind,source=$script,target=/input/inspect.py,readonly" `
  worksite-checkpoint-inspector:8.4.173 /input/inspect.py
```

The container runs as UID/GID 65534. It receives only the checkpoint and inspection
script, with no credentials, home directory, Docker socket, or writable host mount.
It checks the exact SHA-256, uses `weights_only=True` with an explicit list of
reviewed installed model classes, and never falls back to unrestricted loading.
Any unrecognized global or shape mismatch must stop inspection for review.
Docker isolation and restricted loading reduce risk; neither is proof of safety.

The smoke input is a black 320×320 synthetic image, solely for compatibility.
It must never be included as construction-video evaluation, accuracy evidence,
or an annotated demonstration. See PHASE_STATUS.md for actual execution status.

## Class semantics and licensing

The [Construction-PPE documentation](https://docs.ultralytics.com/datasets/detect/construction-ppe/)
lists `helmet`, `gloves`, `vest`, `boots`, `goggles`, `none`, `Person`, `no_helmet`,
`no_goggle`, `no_gloves`, and `no_boots`. These expected labels must be compared
with the actual loaded model metadata. There is no dedicated missing-vest class.
The ambiguous `none` label cannot establish missing vest without annotation review.

SiteGuard declares MIT for its repository, while Ultralytics code/models and the
claimed training dataset carry AGPL terms. Repository licensing does not resolve
the weight's provenance or underlying image rights. Embedded license metadata,
if present, is an upstream statement rather than independent permission evidence.
Do not redistribute the checkpoint until that is resolved. Original project code
uses AGPL-3.0-only as requested.

Fallback: the official COCO-trained `yolo26n.pt` can provide person tracking after
acquisition and verification. It cannot substitute for a specialized PPE classifier.
