#!/usr/bin/env python3
"""Download MediaPipe model files used by the coach demo."""
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

FILES = {
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}


def download(name: str, url: str) -> Path:
    dest = MODELS_DIR / name
    if dest.exists():
        print(f"Already present: {dest}")
        return dest
    print(f"Downloading {name} from {url} ...")
    print("  (this is a ~5.5 MB file; it may take a minute)")
    urllib.request.urlretrieve(url, dest)
    size = dest.stat().st_size
    print(f"Saved {dest} ({size / 1024 / 1024:.1f} MB)")
    return dest


def main():
    for name, url in FILES.items():
        download(name, url)
    print("Models ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCanceled.")
        sys.exit(1)
