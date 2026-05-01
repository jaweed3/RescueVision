"""
benchmark_cpu.py
Validasi constraint C-A3: inferensi per sampel ≤ 3 detik di CPU.

Jalankan DI LAPTOP DEMO (bukan PC lab GPU) sebelum presentasi:
  python src/benchmark_cpu.py --model model/best.onnx --images test_data/images

Output akan menampilkan:
- Waktu inferensi per gambar (mean, p95, max)
- Ukuran model
- Jumlah deteksi per gambar
"""

import argparse
import time
import os
from pathlib import Path
import numpy as np


def load_model(model_path: str):
    import onnxruntime as ort
    # Force CPU provider — simulasi kondisi juri
    providers = ['CPUExecutionProvider']
    session = ort.InferenceSession(model_path, providers=providers)
    return session


def preprocess_image(img_path: str, input_size: int = 640):
    import cv2
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read: {img_path}")
    img_resized = cv2.resize(img, (input_size, input_size))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_norm = img_rgb.astype(np.float32) / 255.0
    img_chw = np.transpose(img_norm, (2, 0, 1))  # HWC → CHW
    img_batch = np.expand_dims(img_chw, axis=0)  # add batch dim
    return img_batch


def run_benchmark(model_path: str, images_dir: str, n_warmup: int = 3,
                  input_size: int = 640, max_images: int = 50):
    print("=" * 60)
    print("RescueVision Edge — CPU Inference Benchmark")
    print(f"Model: {model_path}")
    print(f"Images: {images_dir}")
    print(f"Input size: {input_size}x{input_size}")
    print(f"Device: CPU-only (forced)")
    print("=" * 60)

    # Model size check
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"\nModel size: {model_size_mb:.2f} MB")
    if model_size_mb > 50:
        print("  ❌ CONSTRAINT VIOLATION: Model > 50 MB!")
    else:
        print(f"  ✅ Constraint C-A1 OK: {model_size_mb:.2f} MB ≤ 50 MB")

    # Load model
    print("\nLoading model...")
    t0 = time.time()
    session = load_model(model_path)
    load_time = time.time() - t0
    print(f"  Model loaded in {load_time:.2f}s")

    input_name = session.get_inputs()[0].name

    # Collect image paths
    images_path = Path(images_dir)
    img_files = list(images_path.glob("*.jpg")) + list(images_path.glob("*.png"))
    if len(img_files) == 0:
        print(f"  ❌ No images found in {images_dir}")
        return
    img_files = img_files[:max_images]
    print(f"\nBenchmarking on {len(img_files)} images (max={max_images})")

    # Warmup
    print(f"Warming up ({n_warmup} runs)...")
    for i in range(min(n_warmup, len(img_files))):
        img = preprocess_image(str(img_files[i]), input_size)
        _ = session.run(None, {input_name: img})

    # Benchmark
    times = []
    for img_path in img_files:
        img = preprocess_image(str(img_path), input_size)
        t_start = time.perf_counter()
        outputs = session.run(None, {input_name: img})
        t_end = time.perf_counter()
        times.append(t_end - t_start)

    times = np.array(times)
    mean_t  = np.mean(times)
    p95_t   = np.percentile(times, 95)
    max_t   = np.max(times)
    min_t   = np.min(times)

    print("\n--- RESULTS ---")
    print(f"  Mean inference time : {mean_t*1000:.1f} ms")
    print(f"  P95  inference time : {p95_t*1000:.1f} ms")
    print(f"  Max  inference time : {max_t*1000:.1f} ms")
    print(f"  Min  inference time : {min_t*1000:.1f} ms")

    CONSTRAINT_LIMIT = 3.0  # seconds
    print(f"\nConstraint C-A3: ≤ {CONSTRAINT_LIMIT}s per sample @ CPU")
    if max_t <= CONSTRAINT_LIMIT:
        print(f"  ✅ PASS: max={max_t:.3f}s ≤ {CONSTRAINT_LIMIT}s")
    else:
        print(f"  ❌ FAIL: max={max_t:.3f}s > {CONSTRAINT_LIMIT}s")
        print("     → Coba: kurangi input_size (416 atau 320)")

    print("\n" + "=" * 60)
    print("Simpan output ini sebagai bukti untuk Proposal Bab 3")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",  default="model/best.onnx",
                        help="Path ke ONNX model")
    parser.add_argument("--images", default="test_data/images",
                        help="Folder gambar test")
    parser.add_argument("--size",   type=int, default=640,
                        help="Input image size (try 416 or 320 jika terlalu lambat)")
    parser.add_argument("--max",    type=int, default=50,
                        help="Max images untuk benchmark")
    args = parser.parse_args()

    run_benchmark(args.model, args.images, input_size=args.size, max_images=args.max)
