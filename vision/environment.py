"""Report runtime capabilities without loading any model or exposing credentials."""

import importlib.metadata
import platform
import shutil


def environment_report() -> dict:
    packages = {}
    for name in ("pydantic", "ultralytics", "torch", "torchvision", "numpy", "opencv-python"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "packages": packages,
        "commands": {name: shutil.which(name) is not None for name in ("git", "ffmpeg", "ffprobe")},
        "gpu_execution_verified": False,
    }
