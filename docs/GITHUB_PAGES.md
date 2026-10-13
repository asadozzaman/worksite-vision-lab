# Public research demo

The `site/` directory is a buildless GitHub Pages demo of saved research outputs.
It is separate from the planned inference API and application dashboard. There is
no backend, upload processing, model execution or account system in this site.

Live URL: [Worksite Vision Lab](https://asadozzaman.github.io/worksite-vision-lab/).
Verified on 2026-10-13: GitHub Pages reported `built`, HTTPS enforced, with
`gh-pages` at `/`. Deployment commit: `570d9cae9904876089b166e244304e172a45c87a`;
source implementation: `bae289f767437f654b510b3532d4f291f2f9bfa1`.
All 13 allowlisted files returned HTTP 200 and matched their published hashes;
the manifest matched the reviewed local copy. The live viewer loaded frame 50
at 2.000 seconds and BoT-SORT ID 8 with confidence 0.712.
Source review: [PR #5](https://github.com/asadozzaman/worksite-vision-lab/pull/5).

## Published content

- Six sampled building frames: 0, 25, 50, 75, 100 and 130, from the reviewed CC0 source.
- Exact saved Person predictions and ByteTrack/BoT-SORT output boxes for those frames.
- Fixed settings, source/input hashes and explicit absence of benchmark accuracy.
- Real baseline observations and links to pinned experiment/protocol documents.
- Source attribution, modification notes and a public file checksum manifest.

The original building source is Akum20's
[Men at work in building site](https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm),
under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Public derivatives were resized/resampled, extracted as JPEGs and displayed with
saved prediction overlays. No raw video, weights, street frames, user annotations,
local storage, credentials or backend data directory is published.

## Rebuild and preview

From a checkout with the installed project and original review bundle:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_public_demo --images data/annotation/building/images --manifest data/annotation/building/manifest.json --site data/pages-rebuild
```

The exporter validates all source JPEG hashes and the complete original detection
and tracker streams. Use a new output folder; copy the maintained `site/index.html`,
`style.css`, `app.js`, `icon.svg` and `.nojekyll` into it, then:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_pages data/pages-rebuild
node --test tests/site_payload.test.cjs
node --check site/app.js
python -m http.server 8771 --bind 127.0.0.1 --directory site
```

The Node evidence tests check the tracked `site/` payload against preserved results,
not the alternative local rebuild directory. They verify prediction equivalence,
timestamps, image hashes and the exact public-file allowlist. Browser inspection
checks all overlay modes, frame boundaries, source loading and responsive layout.

The tracked baseline report adds post-run `artifact_validation` to its original
run summary. The exporter reconstructs the original serialization after removing
only that report field, then requires the exact tracker-recorded source-summary
hash. No evaluator source-binding rule is relaxed.

## GitHub publication

GitHub Pages serves static HTML/CSS/JavaScript. The deployment branch is `gh-pages`,
with only the approved site files at its root and `.nojekyll` disabling Jekyll.
The Python project and open research PRs do not need a main-branch merge to publish
this demo. Feature implementation is reviewed separately.

After tests pass and the source changes are committed, publish the committed payload:

```powershell
.\.venv\Scripts\python.exe -m scripts.publish_pages --source HEAD
```

The publisher uses a separate temporary Git index and reads blobs from the selected
commit, never the entire working directory. It creates/fast-forwards `gh-pages`,
preserves prior deployment ancestry and uses a normal push. A divergent local
deployment branch is rejected. It does not merge main or rewrite existing history.
Configure Pages to publish `gh-pages` at `/` using GitHub repository settings or
the Pages API; that initial setting is separate from publishing source commits.

Run `scripts.prepare_pages` after any public-file edit. Publish exactly its
allowlisted files plus `publish-manifest.json`. Check deployed file bytes against
the manifest and verify the viewer at the returned Pages URL before declaring it
live. Do not point Pages at the full workspace or ignored `data/` directory.

Changes to deployment settings or a future backend are separate from this static
demo. A Python inference service requires an appropriate server runtime; GitHub
Pages does not provide that runtime.
