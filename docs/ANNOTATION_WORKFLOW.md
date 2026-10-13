# Person annotation workflow

The local editor creates version 2 **person tracking** reference drafts. It supports
manual boxes and video-local identities, not PPE or event labels. Software checks
do not establish label accuracy. Both existing clips are development data.

## Open the editor

Export with the commands in [tracking reproduction](TRACKING_REPRODUCTION.md),
using a new output folder. No model inference is needed. The exporter checks the
input video and prediction hashes and creates raw JPEG frames, a manifest, an
unreviewed reference template, and a self-contained editor.

On the development machine the new bundles are `data/annotation/building/index.html`
and `data/annotation/street/index.html`. Open either file in a modern browser with
its `images/` folder alongside it. Alternatively:

```powershell
python -m http.server 8769 --bind 127.0.0.1 --directory data/annotation
```

Open `http://127.0.0.1:8769/building/` or `/street/`. Files and browser drafts stay
local. The editor makes no annotation upload or analytics requests. Browser storage
can be unavailable for local files; download JSON regularly. File and localhost
origins have separate drafts. This is an annotation utility; the React application
remains a later phase.

## Annotate and save

1. Enter your reviewer name and choose **Human reviewer** only for your own review.
   Assistant drafts and software tests must use their corresponding reviewer type.
   Keep predictions hidden during initial annotation.
2. Select a contiguous first/last frame interval. Every frame in that interval
   needs inspection; frames outside it remain in the document as unevaluated data.
3. Drag a tight rectangle around the visible extent of each person, including
   distant and cropped people when identifiable as people. Use normalized pixel
   coordinates, origin at top left. Set partial occlusion or truncation when relevant.
4. Assign **New identity** for a new person. Reuse the same `p001`-style identity
   across frames and reappearances when supported by visual continuity. Never copy
   a tracker ID into the manual identity scheme. Identity is video-local, not a name.
5. Use **Copy previous boxes** on an empty next frame to carry manual IDs forward.
   Adjust every copied box. Copy never marks the new frame reviewed. Select a box
   to edit coordinates, identity, attributes or notes; use Delete for a false box.
6. If identity or person visibility is unresolved, mark the box **Exclude / ignore**
   and document the reason. Do not silently omit difficult people. Duplicate IDs in
   a frame are rejected. Future metrics must declare how exclusions are handled.
7. Inspect all boxes and mark the frame reviewed. For a frame with no people,
   explicitly confirm that observation before reviewing it. An empty template is
   not a confirmed negative. Use **Next unreviewed** to find remaining work.
8. Download JSON for a durable copy; reopen it with **Open saved JSON**. Imports
   must match the manifest, video, dimensions, frame rate and frame count. They
   replace the draft only after validation. Browser caching is not a backup.
9. After personally reviewing every selected frame and identity continuity, check
   the human attestation. Every edit clears attestation; frame edits also clear that
   frame's review. Changing reviewer or Undo clears all frame reviews. Undo retains
   an operation history but is limited to the current session's last 30 snapshots.

History is a revision/action log, not a cryptographically authenticated audit of
human behavior. Imported JSON and declarations can be edited externally. Freeze
records the submitted declaration and checks consistency; independent label QA is
still required before using labels as benchmark truth.

## Validate and freeze

Use the lightweight project environment; these commands do not load a model.
Replace the saved JSON path below with the actual downloaded reference.

```powershell
worksite validate-reference data/references/building-reviewed.json --manifest data/annotation/building/manifest.json
worksite freeze-reference data/references/building-reviewed.json --manifest data/annotation/building/manifest.json --images data/annotation/building/images --output data/references/building-v1
```

Validation accepts a consistent unfinished draft and reports `ready_to_freeze:false`.
Freeze requires a complete selected interval, a named human reviewer, explicit
attestation and revision history. It rechecks **all** source JPEG hashes and refuses
an existing output directory. It copies the exact annotation and manifest bytes,
then writes `freeze.json` with their SHA-256 hashes, interval, reviewer and version.
Keep the original images; freeze does not duplicate them. Freeze does not calculate
accuracy or certify annotation quality. Do not modify a frozen set; create a new
version and record why if corrections are needed.

Version 1 empty templates from the earlier evidence viewer are not imported by the
new editor. Export a new bundle; do not relabel an old file as schema version 2.

## Verification performed on 2026-10-12

- Windows Python 3.10: 79 foundation tests passed, including 25 reference/render
  tests. The lightweight environment intentionally skips the vision integration
  module; the existing dedicated CI job covers that dependency set.
- Node 22: seven editor-state tests passed; UI JavaScript syntax checked. CI now
  runs the Node tests in a separate job, alongside the existing Python matrix.
- Real building/street bundles exported: 131 + 167 raw frames, all templates
  unreviewed. No new model inference or human annotation was performed.
- Browser software test: drew a box, verified unresolved-ID review rejection,
  assigned a manual ID, reviewed one test frame, copied to the next frame, rejected
  out-of-bounds coordinates, downloaded JSON, used Undo, and reopened the saved file.
  Wrong-clip import was rejected without replacing the draft.
- The browser-generated software fixture passed the Python validator and was
  refused by the freeze gate. It is explicitly **not human reference data**. The
  browser draft was restored to the empty template after testing.

Next research gate: a human completes and checks contiguous person labels, then
freezes a version. Establish a distinct held-out scene before selecting a method
for final accuracy evaluation. Follow [the annotation protocol](ANNOTATION_PROTOCOL.md)
for metric definitions and later PPE/event annotation.
