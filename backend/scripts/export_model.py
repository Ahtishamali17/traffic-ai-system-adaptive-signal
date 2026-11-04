"""
scripts/export_model.py
--------------------------------------------------------------------
Exports a trained/stock YOLOv8 .pt checkpoint to a faster inference
format: ONNX (portable, CPU/GPU) or TensorRT engine (NVIDIA GPU only,
fastest, but the resulting .engine file is hardware- and
TensorRT-version-specific and must be rebuilt on each deployment
target).

Usage:
    python scripts/export_model.py --weights models/weights/yolov8n.pt --format onnx
    python scripts/export_model.py --weights models/weights/yolov8n.pt --format engine --half

After exporting, point MODEL_WEIGHTS_PATH in .env at the new file.
VehicleDetector (app/services/detector.py) loads whatever Ultralytics
YOLO() accepts, which includes .onnx and .engine files transparently.
--------------------------------------------------------------------
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a YOLOv8 model to ONNX or TensorRT")
    parser.add_argument("--weights", required=True, help="Path to the source .pt checkpoint")
    parser.add_argument(
        "--format", choices=["onnx", "engine"], default="onnx",
        help="onnx = portable CPU/GPU format. engine = TensorRT, NVIDIA GPU only, fastest.",
    )
    parser.add_argument("--half", action="store_true", help="Export in FP16 (GPU only, ~2x smaller/faster)")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size the export is optimized for")
    parser.add_argument(
        "--dynamic", action="store_true",
        help="Allow variable input size at inference time (ONNX only; slightly slower than fixed size)",
    )
    args = parser.parse_args()

    from ultralytics import YOLO  # imported here so --help works without the dependency installed

    model = YOLO(args.weights)

    print(f"Exporting {args.weights} -> {args.format} (imgsz={args.imgsz}, half={args.half})")
    export_path = model.export(
        format=args.format,
        half=args.half,
        imgsz=args.imgsz,
        dynamic=args.dynamic if args.format == "onnx" else False,
    )
    print(f"Exported to: {export_path}")
    print(
        f"Set MODEL_WEIGHTS_PATH={export_path} in backend/.env to use it, "
        f"and set DEVICE=cuda if this is a TensorRT engine."
    )


if __name__ == "__main__":
    main()
