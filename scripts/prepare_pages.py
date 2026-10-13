"""Validate the exact public file allowlist and write a GitHub Pages publish manifest."""

import argparse
import json
from pathlib import Path

from vision.provenance import sha256_file

FILES = {
    ".nojekyll",
    "index.html",
    "style.css",
    "app.js",
    "icon.svg",
    "results.json",
    "assets/baseline-comparison.png",
    *(f"assets/frames/{index:06d}.jpg" for index in (0, 25, 50, 75, 100, 130)),
}


def prepare(site):
    root = site.resolve(strict=True)
    entries = list(site.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("public payload must not contain symlinks")
    files = {path.relative_to(site).as_posix(): path for path in entries if path.is_file()}
    if set(files) - {"publish-manifest.json"} != FILES:
        raise ValueError("public payload differs from the approved file allowlist")
    if any(not path.resolve().is_relative_to(root) for path in files.values()):
        raise ValueError("public payload escapes the site directory")
    data = json.loads(files["results.json"].read_bytes())
    if data["scope"] != "saved_person_predictions_only" or data["accuracy"] is not None:
        raise ValueError("public demo must not claim measured accuracy")
    for frame in data["frames"]:
        path = files.get(frame["image"])
        if path is None or sha256_file(path) != frame["image_sha256"]:
            raise ValueError("public image differs from its source-bound record")
    record = {
        "schema_version": 1,
        "hosting": "GitHub Pages",
        "scope": data["scope"],
        "evidence_source_commit": data["source_commit"],
        "accuracy_measured": False,
        "files": [
            {"path": name, "bytes": files[name].stat().st_size, "sha256": sha256_file(files[name])}
            for name in sorted(FILES)
        ],
        "manifest_note": (
            "This manifest does not hash itself. "
            "No user annotations or model weights are published."
        ),
    }
    (site / "publish-manifest.json").write_bytes(
        (json.dumps(record, indent=2) + "\n").encode("utf-8")
    )
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    record = prepare(args.site)
    print(json.dumps({"approved_files": len(record["files"]), "scope": record["scope"]}))
