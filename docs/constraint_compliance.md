# Constraint Compliance Documentation
## RescueVision Edge — Track A: The Edge Vision
### Proposal Bab 3: Kepatuhan Constraint

---

## C-A1: Ukuran Model ≤ 50 MB

**Requirement:** File model final (.pt / .h5 / .onnx) tidak boleh melebihi 50 MB.

**Implementation:**
- Architecture: YOLOv8n (nano variant) — smallest official YOLOv8 model
- Parameter count: ~3.2M parameters
- PyTorch weights (best.pt): ~6.2 MB
- **ONNX export (model.onnx): ~11–13 MB** ← file yang disubmit untuk inference

**Why YOLOv8n fits the constraint:**
YOLOv8n uses a C2f backbone (lightweight CSP bottleneck with 2 fast layers) dengan
depth_multiple=0.33 dan width_multiple=0.25, menghasilkan model yang ~5x lebih kecil
dari YOLOv8m sambil tetap mampu mendeteksi objek kecil berkat arsitektur anchor-free.

**Verification:**
```
model.onnx → X.XX MB < 50 MB ✓ (measured post-export)
```

---

## C-A2: Kompatibilitas Platform (CPU-only capable)

**Requirement:** Model wajib tetap dapat berjalan di lingkungan CPU-only.

**Implementation:**
- Inference engine: **ONNX Runtime** dengan `CPUExecutionProvider`
- Zero GPU dependency di `inference.ipynb`
- Session initialization:
  ```python
  session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
  ```
- Tidak ada `torch.cuda`, tidak ada `device='cuda'` di inference pipeline

**Why ONNX Runtime for CPU:**
ONNX Runtime dengan CPUExecutionProvider menggunakan OpenMP threading dan
MLAS (Microsoft Linear Algebra Subprograms) yang dioptimasi untuk x86/ARM CPU,
memberikan inference lebih cepat daripada PyTorch CPU mode untuk model kecil.

---

## C-A3: Kecepatan Inferensi ≤ 3 detik (CPU, Intel Core i5 Gen 8+)

**Requirement:** Waktu inferensi per satu sampel TIDAK BOLEH melebihi 3 detik pada CPU standar.

**Implementation choices specifically to meet this constraint:**

| Design Decision | Value | Rationale |
|---|---|---|
| Input resolution | 416×416 px | Balance accuracy vs speed; 640px terlalu lambat di CPU lama |
| Model variant | YOLOv8n (nano) | 3.2M params vs 25.9M (YOLOv8m) — ~8x faster inference |
| Export format | ONNX (simplified graph) | Eliminates PyTorch overhead; faster than .pt on CPU |
| ONNX opset | 12 | Wide compatibility without sacrificing optimization |
| Graph simplification | `simplify=True` | Fuses BatchNorm, removes redundant ops |
| Input shape | Fixed (not dynamic) | Deterministic inference time, no shape inference overhead |

**Benchmark results:** (lihat `docs/cpu_benchmark.txt` setelah dijalankan di mesin demo)
```
CPU: Intel Core i5-XXXX (placeholder — run benchmark_cpu.py)
Mean inference: XX ms
Max inference:  XX ms
Constraint: PASS (XX ms < 3000 ms)
```

**Expected performance range:**
- Intel Core i5 Gen 8 @ 416px: ~200–600ms per image
- Intel Core i5 Gen 11+ @ 416px: ~100–300ms per image
- Both well within 3000ms limit

---

## C-A4: Framework

**Requirement:** Model wajib menggunakan PyTorch, TensorFlow/Keras, atau ONNX Runtime.

**Implementation:**
- **Training:** PyTorch via Ultralytics (YOLOv8)
- **Inference:** ONNX Runtime (CPUExecutionProvider)

Ini adalah workflow yang direkomendasikan secara resmi:
train in PyTorch → export ONNX → deploy with ONNX Runtime.
Kedua framework yang digunakan adalah framework yang tercantum dalam constraint.

---

## C-A5: Offline Total

**Requirement:** Seluruh proses inferensi berjalan secara offline. Dilarang menggunakan API eksternal.

**Implementation:**
- Zero external API calls di seluruh `inference.ipynb`
- Model dimuat dari file lokal (`model.onnx`)
- Tidak ada `requests`, tidak ada `urllib`, tidak ada cloud SDK
- Tidak ada Google Vision API, tidak ada AWS Rekognition
- Dataset digunakan secara lokal (tidak di-fetch saat runtime)

**Verification:**
Seluruh dependency di `requirements.txt` adalah library lokal (onnxruntime, opencv-python, numpy).
Tidak ada Hugging Face Inference API, tidak ada OpenAI, tidak ada third-party inference endpoint.

---

## Constraint Umum

### 1. Struktur File
```
✓ proposal.pdf          — Dokumen proposal lengkap
✓ training.ipynb        — Training pipeline dengan log terlihat  
✓ inference.ipynb       — Script inferensi bersih
✓ model.onnx            — File model final
✓ train_data/           — Data training + validasi
✓ test_data/            — Data testing (terpisah)
```

### 2. Reproducibility
Training dapat dijalankan ulang dari `training.ipynb` dengan dataset yang sama.
Seluruh hyperparameter tercatat di `CONFIG` dict di sel pertama training notebook.
Random seed di-set secara implisit oleh Ultralytics untuk reproducibility.

### 3. Bahasa Kode
Python (100%). Seluruh kode menggunakan Python 3.10+.

### 4. Larangan Cloud Inference
**Zero cloud inference.** Tidak ada API key, tidak ada endpoint eksternal.
Seluruh model weights disimpan lokal di `model.onnx`.

### 5. Proposal Bab 3
Dokumen ini adalah draft untuk Proposal Bab 3.
Wajib dipindahkan dan diformat ke dalam file `proposal.pdf` sebelum submission.
