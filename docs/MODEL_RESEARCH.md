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

Additional static opcode inspection reads top-level strings identifying
Ultralytics `8.4.37`, date `2026-04-19T20:34:11.690588`, and license
`AGPL-3.0 (https://ultralytics.com/license)`. These are embedded producer statements,
not independently authenticated training records. The dynamic verification report
will preserve them alongside actual loaded metadata.

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
New-Item -ItemType Directory -Force data/quarantine | Out-Null
$url = 'https://raw.githubusercontent.com/C-Nekopedia/SiteGuard/f4d1a097679439f3eaec4e5569d4e52d479cf592/data/models/yolo26n_ppe.pt'
Invoke-WebRequest $url -OutFile data/quarantine/yolo26n_ppe.pt
$expected = 'b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3'
if ((Get-FileHash data/quarantine/yolo26n_ppe.pt).Hash.ToLower() -ne $expected) {
  throw 'Checkpoint hash mismatch; stop inspection'
}
worksite inspect-checkpoint data/quarantine/yolo26n_ppe.pt
docker build -f docker/checkpoint-inspector.Dockerfile -t worksite-checkpoint-inspector:8.4.173 .
$model = (Resolve-Path data/quarantine/yolo26n_ppe.pt).Path
$script = (Resolve-Path scripts/inspect_model_isolated.py).Path
$vision = (Resolve-Path vision).Path
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges `
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,noexec,nosuid,size=256m `
  -e PYTHONPATH=/src --mount "type=bind,source=$vision,target=/src/vision,readonly" `
  --mount "type=bind,source=$model,target=/input/model.pt,readonly" `
  --mount "type=bind,source=$script,target=/input/model_check.py,readonly" `
  worksite-checkpoint-inspector:8.4.173 /input/model_check.py
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

Inspection of the upstream
[detection service](https://github.com/C-Nekopedia/SiteGuard/blob/main/apps/server/app/services/detection_service.py)
found frame-wide helmet-presence gating and a `none` → missing-vest mapping.
Neither establishes correct worker-to-PPE ownership or the meaning of ambiguous
training labels. No source from that application is copied into this project.

The [Construction-PPE documentation](https://docs.ultralytics.com/datasets/detect/construction-ppe/)
lists `helmet`, `gloves`, `vest`, `boots`, `goggles`, `none`, `Person`, `no_helmet`,
`no_goggle`, `no_gloves`, and `no_boots`. These expected labels must be compared
with the actual loaded model metadata. There is no dedicated missing-vest class.
The ambiguous `none` label cannot establish missing vest without annotation review.

SiteGuard declares MIT for its repository, while the checkpoint itself embeds an
AGPL-3.0 statement and Ultralytics code/models and the claimed training dataset
carry AGPL terms. Repository licensing does not resolve
the weight's provenance or underlying image rights. Embedded license metadata,
if present, is an upstream statement rather than independent permission evidence.
Do not redistribute the checkpoint until that is resolved. Original project code
uses AGPL-3.0-only as requested.

Fallback: the official COCO-trained `yolo26n.pt` can provide person tracking after
acquisition and verification. It cannot substitute for a specialized PPE classifier.

## Executed verification and compatibility finding

Restricted loading succeeded in the offline container: Python 3.11.17,
Torch 2.7.0+cpu and Ultralytics 8.4.173. Actual loaded labels match the 11 labels
listed above, including `Person` at index 6. The checkpoint contains **2,508,090
parameters**; exact state-dict keys/shapes load into a fresh official YOLO26n with
11 classes. The black-image smoke returned one result and zero boxes. This
demonstrates compatibility, not accuracy. See [final evidence](evidence/checkpoint-isolated.json).

The initial raw-object inspection reported `end2end: false`. Source comparison
explained why: [8.4.37 Detect.end2end](https://github.com/ultralytics/ultralytics/blob/v8.4.37/ultralytics/nn/modules/head.py)
defaults a missing `_end2end` to true, whereas
[8.4.173](https://github.com/ultralytics/ultralytics/blob/v8.4.173/ultralytics/nn/modules/head.py)
defaults it to false. This artifact has both trained heads but no explicit flag.
The audited loader reconstructs the architecture, strictly transfers weights and
explicitly restores the original true behavior. Both real-video runs use this
same documented setting. The current package warns that `end2end=True` is deprecated
in favor of `nms=False`; the tested baseline retains the explicit original setting.

An initial container script mount named `inspect.py` shadowed Python's standard
library `inspect` and failed before checkpoint loading. Renaming the mount to
`model_check.py` fixed it. Both this failure and the mode discrepancy are retained
in the experiment log rather than hidden.

The checkpoint is suitable for a restricted, attributed AGPL research baseline.
Embedded AGPL metadata plus the repository's declared training source are recorded;
original training-data rights and split integrity remain unaudited. There is no
weight redistribution, commercial-use clearance or reproduced training metric.
