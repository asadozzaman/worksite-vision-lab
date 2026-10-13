# Building baseline figure

[figure.png](figure.png) shows the actual normalized building video at zero-based
frame 50, 2.000 seconds: raw input, saved Person detections and saved BoT-SORT tracks.
No inference or reference annotation was performed to produce this figure. Other
PPE classes are intentionally omitted from the detection panel.

Source: [Men at work in building site](https://commons.wikimedia.org/wiki/File:Men_at_work_in_building_site.webm),
Akum20, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Modifications: resizing, resampling, prediction overlays and comparison layout.
The source video stays outside Git. The figure makes no safety violation,
endorsement or verified accuracy claim.

## Reproduce

Acquire and normalize the source according to [baseline setup](../../BASELINE_REPRODUCTION.md).
Use an installed project environment with OpenCV/NumPy, or the tracking container
with the equivalent mounts. Run from the repository root into a new folder:

```powershell
python -m scripts.render_baseline_figure --video data/normalized/building.mp4 --frame 50 --output data/figures/building-baseline-repeat
```

The renderer uses the committed building baseline and BoT-SORT records. It checks
the exact normalized video hash, source-model/settings binding, both complete
prediction streams, their hashes, and decoded video dimensions/frame count before
writing. It refuses an existing output folder. All boxes come from saved outputs;
display clipping changes drawing coordinates only.

The committed baseline report adds post-run `artifact_validation` to the original
run summary. The renderer removes only that report field, reconstructs its original
UTF-8 indented JSON serialization, and requires the resulting hash to match the
tracker's recorded source-summary hash. That reconstruction was also compared
byte-for-byte with the original local summary. It does not relax evaluator checks
or edit historical results.

[manifest.json](manifest.json) records source, decoded BGR pixel hash, input-file
hashes, original summary hash, renderer hash and rendering runtime. OpenCV 4.13.0
was used only for this figure's decoding/drawing; the inference and tracking runs
retain their separately recorded OpenCV 4.11.0 environment. PNG encoding, fonts or
decoded pixels can vary across library builds. The manifest identifies this render,
and no image hash is presented as a cross-platform guarantee.
