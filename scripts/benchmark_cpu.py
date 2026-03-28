"""
benchmark_cpu.py
----------------
Measures CPU inference time of the ONNX model.
This script proves compliance with Constraint C-A3:
  - Single inference ≤ 3 seconds on Intel Core i5 Gen 8+ (CPU only)

Run this on the target machine (no GPU) before submission.
Output is logged to docs/cpu_benchmark.txt

Usage:
    python scripts/benchmark_cpu.py --model model.onnx --images test_data/images/
    python scripts/benchmark_cpu.py --model model.onnx --images test_data/images/ --n 50
"""

import argparse
import time
import os
import psutil
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
INPUT_SIZE = 416  # Must match training imgsz


def load_onnx_model(model_path: str):
    import onnxruntime as ort
    # Force CPU — no GPU acceleration
    providers = ['CPUExecutionProvider']
    session = ort.InferenceSession(model_path, providers=providers)
    return session


def preprocess_image(img_path: str, input_size: int = INPUT_SIZE):
    """Load and preprocess image to model input format."""
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}")
    
    # Letterbox resize (maintain aspect ratio)
    h, w = img.shape[:2]
    scale = input_size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)
    img_resized = cv2.resize(img, (new_w, new_h))
    
    # Pad to square
    padded = np.zeros((input_size, input_size, 3), dtype=np.uint8)
    padded[:new_h, :new_w] = img_resized
    
    # Normalize and convert to NCHW float32
    img_float = padded.astype(np.float32) / 255.0
    img_nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...]
    
    return img_nchw


def run_benchmark(session, image_paths: list, n_samples: int):
    """Run inference on n_samples images and record timing."""
    times = []
    input_name = session.get_inputs()[0].name
    
    # Warmup (3 runs)
    print("Warming up (3 runs)...")
    for i in range(min(3, len(image_paths))):
        img = preprocess_image(str(image_paths[i]))
        _ = session.run(None, {input_name: img})
    
    # Benchmark
    print(f"Benchmarking {n_samples} images...")
    sample_paths = image_paths[:n_samples]
    
    for img_path in sample_paths:
        img = preprocess_image(str(img_path))
        
        start = time.perf_counter()
        _ = session.run(None, {input_name: img})
        end = time.perf_counter()
        
        times.append((end - start) * 1000)  # ms
    
    return times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='model.onnx')
    parser.add_argument('--images', type=str, default='test_data/images')
    parser.add_argument('--n', type=int, default=30, help='Number of images to benchmark')
    args = parser.parse_args()
    
    model_path = ROOT / args.model
    images_dir = ROOT / args.images
    
    if not model_path.exists():
        print(f"ERROR: Model not found: {model_path}")
        print("Run training first and export to ONNX.")
        return
    
    # Get image list
    image_paths = sorted(list(images_dir.rglob("*.jpg")) + list(images_dir.rglob("*.png")))
    if len(image_paths) == 0:
        print(f"ERROR: No images found in {images_dir}")
        return
    
    n_samples = min(args.n, len(image_paths))
    
    print("="*60)
    print("RescueVision Edge — CPU Inference Benchmark")
    print(f"Date: {datetime.now().isoformat()}")
    print("="*60)
    
    # System info
    cpu_info = f"{psutil.cpu_count(logical=False)} cores ({psutil.cpu_count()} logical)"
    ram_gb = psutil.virtual_memory().total / (1024**3)
    model_mb = os.path.getsize(model_path) / (1024**2)
    
    print(f"\nSystem:")
    print(f"  CPU: {cpu_info}")
    print(f"  RAM: {ram_gb:.1f} GB")
    print(f"\nModel: {model_path.name} ({model_mb:.2f} MB)")
    print(f"Input size: {INPUT_SIZE}x{INPUT_SIZE}")
    print(f"Samples: {n_samples}")
    
    # Load model
    print("\nLoading ONNX model (CPU only)...")
    session = load_onnx_model(str(model_path))
    
    # Run benchmark
    times_ms = run_benchmark(session, image_paths, n_samples)
    
    # Statistics
    times_arr = np.array(times_ms)
    mean_ms  = np.mean(times_arr)
    std_ms   = np.std(times_arr)
    p50_ms   = np.percentile(times_arr, 50)
    p95_ms   = np.percentile(times_arr, 95)
    p99_ms   = np.percentile(times_arr, 99)
    max_ms   = np.max(times_arr)
    
    LIMIT_MS = 3000  # 3 second constraint
    
    print(f"\n{'='*60}")
    print("RESULTS:")
    print(f"  Mean:    {mean_ms:.1f} ms")
    print(f"  Std:     {std_ms:.1f} ms")
    print(f"  P50:     {p50_ms:.1f} ms")
    print(f"  P95:     {p95_ms:.1f} ms")
    print(f"  P99:     {p99_ms:.1f} ms")
    print(f"  Max:     {max_ms:.1f} ms")
    print(f"\nConstraint C-A3 limit: {LIMIT_MS} ms")
    
    passed = max_ms < LIMIT_MS
    status = "PASS" if passed else "FAIL"
    margin = LIMIT_MS - max_ms
    
    print(f"\nVERDICT: {status}")
    if passed:
        print(f"  Max inference {max_ms:.1f}ms < {LIMIT_MS}ms (margin: {margin:.0f}ms)")
    else:
        print(f"  Max inference {max_ms:.1f}ms EXCEEDS {LIMIT_MS}ms limit!")
        print("  Consider: reduce input size, apply INT8 quantization, or optimize model")
    
    # Save report
    report_path = ROOT / 'docs' / 'cpu_benchmark.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(f"RescueVision Edge — CPU Inference Benchmark\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"System:\n")
        f.write(f"  CPU: {cpu_info}\n")
        f.write(f"  RAM: {ram_gb:.1f} GB\n\n")
        f.write(f"Model: {model_path.name} ({model_mb:.2f} MB)\n")
        f.write(f"Input size: {INPUT_SIZE}x{INPUT_SIZE}\n")
        f.write(f"Samples: {n_samples}\n\n")
        f.write(f"Results:\n")
        f.write(f"  Mean:  {mean_ms:.1f} ms\n")
        f.write(f"  P50:   {p50_ms:.1f} ms\n")
        f.write(f"  P95:   {p95_ms:.1f} ms\n")
        f.write(f"  P99:   {p99_ms:.1f} ms\n")
        f.write(f"  Max:   {max_ms:.1f} ms\n\n")
        f.write(f"Constraint C-A3 limit: {LIMIT_MS} ms\n")
        f.write(f"VERDICT: {status} (max {max_ms:.1f}ms, margin {margin:.0f}ms)\n")
    
    print(f"\nReport saved to: {report_path}")


if __name__ == '__main__':
    main()
