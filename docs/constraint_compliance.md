# Constraint Compliance — Track A: The Edge Vision
## Proposal Bab 3 Draft

### C-A1: Model Size ≤ 50 MB
- Architecture: YOLOv8n (anchor-free, 3.2M params)
- ONNX export: ~11–13 MB << 50 MB ✓
- Verified post-export: see docs/cpu_benchmark.txt

### C-A2: CPU-Only Compatible
- Inference via ONNX Runtime: `providers=['CPUExecutionProvider']`
- Zero CUDA/GPU dependency in inference.ipynb
- Validated on CPU before submission

### C-A3: Inference ≤ 3s per image (i5 Gen 8+)
- Input resolution: 640×640 (balanced for accuracy vs speed)
- ONNX graph simplified at export
- Expected: 200–600ms on i5 Gen 8 — see docs/cpu_benchmark.txt

### C-A4: Framework
- Training: PyTorch (Ultralytics YOLOv8)
- Inference: ONNX Runtime ← listed in constraint

### C-A5: Offline Total
- Zero external API calls in inference pipeline
- Model loaded from local file (model.onnx)
- No requests/urllib/cloud SDK imported

### Architecture Selection Justification (Bab 2)
See docs/architecture_comparison.txt after running experiment_yolov5n_baseline.ipynb.
YOLOv5n trained first as baseline per panitia requirement;
YOLOv8n selected if it achieves higher mAP@0.5 while satisfying all constraints.
