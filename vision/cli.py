"""Phase 0 command line tools. Deliberately does not expose unsafe model loading."""

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from pydantic import ValidationError

from vision.checkpoint import inspect_checkpoint
from vision.config import ExperimentConfig
from vision.environment import environment_report
from vision.evaluation.reference import freeze_reference, reference_status, validate_reference
from vision.provenance import AssetManifest
from vision.video import probe_video


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Worksite Vision Lab research foundation")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="report environment capabilities")
    for command, help_text in (
        ("inspect-checkpoint", "inspect ZIP/pickle metadata without loading"),
        ("validate-assets", "validate an asset provenance manifest"),
        ("validate-config", "validate experiment settings"),
        ("probe-video", "measure local video metadata using ffprobe"),
    ):
        subparser = commands.add_parser(command, help=help_text)
        subparser.add_argument("path", type=Path)
    for command in ("validate-reference", "freeze-reference"):
        subparser = commands.add_parser(command, help="validate or freeze a person reference")
        subparser.add_argument("path", type=Path)
        subparser.add_argument("--manifest", type=Path, required=True)
        if command == "freeze-reference":
            subparser.add_argument("--images", type=Path, required=True)
            subparser.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser(
        "evaluate-person", help="score frozen person labels and both trackers"
    )
    for name in ("reference", "images", "video", "baseline", "config", "output"):
        evaluate.add_argument(f"--{name}", type=Path, required=True)
    evaluate.add_argument("--tracking", type=Path, nargs=2, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = environment_report()
        elif args.command == "inspect-checkpoint":
            result = inspect_checkpoint(args.path)
        elif args.command == "probe-video":
            result = probe_video(args.path)
        elif args.command == "validate-reference":
            reference, _ = validate_reference(args.path, args.manifest)
            result = reference_status(reference)
        elif args.command == "freeze-reference":
            result = freeze_reference(args.path, args.manifest, args.images, args.output)
        elif args.command == "evaluate-person":
            from vision.evaluation.run import evaluate_person

            result = evaluate_person(
                args.reference,
                args.images,
                args.video,
                args.baseline,
                args.tracking,
                args.config,
                args.output,
            )
        else:
            schema = AssetManifest if args.command == "validate-assets" else ExperimentConfig
            validated = schema.model_validate_json(args.path.read_text(encoding="utf-8"))
            result = {"valid": True, "document": validated.model_dump(mode="json")}
    except (
        OSError,
        ValueError,
        ValidationError,
        zipfile.BadZipFile,
        subprocess.TimeoutExpired,
    ) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
