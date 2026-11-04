"""
scripts/download_weights.py
--------------------------------------------------------------------
Pre-downloads a stock YOLOv8 checkpoint into models/weights/ so the
first API request doesn't pay the download cost, and so Docker
images can bake the weights in at build time if desired.

Usage:
    python scripts/download_weights.py --model yolov8n.pt
    python scripts/download_weights.py --model yolov8s.pt
--------------------------------------------------------------------
"""

import argparse
from pathlib import Path

VALID_MODELS = {"yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a stock YOLOv8 checkpoint")
    parser.add_argument(
        "--model", default="yolov8n.pt", choices=sorted(VALID_MODELS),
        help="Which stock YOLOv8 checkpoint to download (n=fastest/smallest, x=most accurate/slowest)",
    )
    parser.add_argument(
        "--dest", default="models/weights",
        help="Destination directory (default: models/weights)",
    )
    args = parser.parse_args()

    from ultralytics import YOLO  # imported here so --help works without the dependency installed

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {args.model} ...")
    model = YOLO(args.model)  # triggers auto-download to ultralytics' cache

    dest_path = dest_dir / args.model
    # Ultralytics caches to its own dir; copy the resolved weights file next to it.
    import shutil
    source_path = Path(model.ckpt_path) if hasattr(model, "ckpt_path") else None
    if source_path and source_path.exists():
        shutil.copy(source_path, dest_path)
        print(f"Saved weights to {dest_path}")
    else:
        print(
            f"Downloaded via Ultralytics cache. Set MODEL_WEIGHTS_PATH={args.model} "
            f"in .env to let the app auto-resolve it, or manually copy the cached "
            f"file to {dest_path}."
        )


if __name__ == "__main__":
    main()
