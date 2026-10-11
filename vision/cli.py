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
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = environment_report()
        elif args.command == "inspect-checkpoint":
            result = inspect_checkpoint(args.path)
        elif args.command == "probe-video":
            result = probe_video(args.path)
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
