# Asset acquisition and review

Status: 2026-10-10. The registry is [assets.json](assets.json); external binaries
belong under ignored `data/` and must not be committed.

## Acquired open-license alternatives

To keep research progressing without automated Pexels collection, two Commons
files were downloaded through their published original-file links:

- [Men at work in building site](https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm),
  Akum20, CC0. Measured 6,674,729 bytes, VP8, 1080×1920, 25 fps, 5.243 s.
  One-second contact-sheet samples inspected by the assistant show a foreground
  material-mixing worker, a worker cropped at the top/right, and distant people.
  Foreground head and torso are visible without a visible helmet or high-visibility
  vest in those samples; this is a visual observation, not a certified violation
  or a human-annotated reference. Suitable for a small qualitative detection test,
  with limitations from short duration, truncation and tiny background workers.
- [Manual workers 2026](https://commons.wikimedia.org/wiki/File:Manual_workers_2026.webm),
  KabanDanish, CC BY 4.0. Measured 6,080,478 bytes, VP9, 720×1280, 30 fps,
  6.761 s. One-second samples show street works behind barriers, multiple people,
  bright workwear, zoom, blur and passing traffic. Useful contrast to the first
  clip. FFmpeg reported an Opus audio packet warning while decoding the contact
  sheet; drop audio for analysis and verify full video decoding. No violation or
  identity ground truth is inferred from these samples.
- [Workers on the roof](https://commons.wikimedia.org/wiki/File:Workers_on_the_roof.webm),
  Eric Harrison, CC BY-SA 2.0. Measured 13,600,616 bytes, VP9, 1920×1080,
  24000/1001 fps, 24.923 s. Five-second samples show helicopter/rooftop activity
  from a distant viewpoint; worker/PPE detail is too small for a useful first PPE
  baseline. **Rejected as a primary PPE evaluation clip.** Retain provenance of
  this unsuccessful acquisition. No violation labels inferred.

Probe JSON files in `docs/evidence/` retain `content_reviewed: false` because the
automated probe cannot establish visual review. The separate notes above record
the limited assistant review performed afterward, not full human ground truth.
All source footage and local contact sheets remain under ignored `data/`.

## Candidate real videos

| Source | Publisher | Publisher metadata (not measured) |
|---|---|---|
| [38885275](https://www.pexels.com/video/urban-construction-scene-with-workers-in-safety-gear-38885275/) | Kiwi and Camera | 1920×1080, 25 fps, 14 seconds; 2026-08-05 |
| [8965526](https://www.pexels.com/video/construction-workers-walking-at-the-construction-site-8965526/) | Mikael Blomkvist | 2160×3840, 25 fps, 13 seconds; 2021-07-28 |

The portrait clip offers a candidate viewpoint difference. Neither file has been
acquired or visually inspected. Worker count, occlusion, small-PPE visibility,
motion continuity and violations remain unverified; titles are not ground truth.

The [Pexels license](https://www.pexels.com/license/) allows use and modification
without mandatory attribution. The [full terms](https://www.pexels.com/terms-of-service/)
also restrict standalone distribution, misleading portrayal, and unauthorized
automated collection (§8). Identifiable-person rights need separate consideration.
Do not scrape the video endpoints or publish claims about depicted workers.

### Manual acquisition

1. Open each linked source page in a browser and use its normal **Free download**
   control after reviewing the terms. Prefer an HD variant for a small first run.
2. Save as `data/videos/pexels-38885275.mp4` and
   `data/videos/pexels-8965526.mp4`; preserve originals.
3. Run `worksite probe-video <path>`. Record measured metadata, byte count and
   SHA-256 in the manifest; keep publisher metadata separate.
4. Review the entire clip and representative frames. Record visible workers,
   PPE visibility, camera motion, occlusion, and suitability. Label uncertain
   regions explicitly. Do not claim violations without frame-level evidence.
5. Freeze normalized inputs and a reviewed annotation subset before comparison.

No videos are uploaded to Kaggle or redistributed here. Pexels footage is a
candidate for demonstration, not automatically a representative safety benchmark.

## Evaluation data

[Construction-PPE](https://docs.ultralytics.com/datasets/detect/construction-ppe/)
is documented as AGPL-3.0 with 11 labels. It is a candidate for detector evaluation
after examining the actual archive, image rights, labels and leakage. Because the
candidate checkpoint claims training on it, its training images cannot be an
independent test. Tracking and event evaluation require separate video annotations.

No dataset has been downloaded and no training is scheduled. Acquire only what the
current acceptance gate requires.
