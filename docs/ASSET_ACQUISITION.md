# Asset acquisition and review

Status: 2026-10-10. The registry is [assets.json](assets.json); external binaries
belong under ignored `data/` and must not be committed.

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
