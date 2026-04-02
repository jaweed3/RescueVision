# BAB 3: KEPATUHAN CONSTRAINT

Bab ini menjelaskan secara rinci bagaimana sistem RescueVision Edge
memenuhi setiap poin *constraint* Track A: The Edge Vision yang ditetapkan
panitia Hackathon FindIT! 2026, beserta bukti teknis yang dapat diverifikasi.

---

## 3.1 Constraint Track A: The Edge Vision

### C-A1: Ukuran Model ≤ 50 MB

**Requirement:** Bobot model final (file .pt / .h5 / .onnx) tidak boleh
melebihi 50 MB.

**Implementasi:**

Model final diekspor dalam format ONNX menggunakan Ultralytics export
pipeline dengan konfigurasi `opset=12`, `simplify=True`, dan
`dynamic=False`. Proses simplifikasi graf dilakukan menggunakan
`onnxslim 0.1.90` yang menggabungkan operasi BatchNorm, menghapus node
redundan, dan mengoptimalkan struktur komputasi tanpa mengubah output
model.

**Hasil terukur:**

| File | Ukuran | Status |
|---|---|---|
| `runs/.../best.pt` (PyTorch) | 18.44 MB | — |
| `model.onnx` (submission) | **12.27 MB** | **PASS ✓** |

Ukuran 12.27 MB berada 75.5% di bawah batas maksimum 50 MB, memberikan
margin yang sangat besar. Pilihan arsitektur YOLOv8n dengan
`depth_multiple=0.33` dan `width_multiple=0.25` secara fundamental
memastikan ukuran model tetap kecil (3.011.043 parameter, 8.2 GFLOPs).

**Verifikasi:**
```python
import os
print(os.path.getsize('model.onnx') / 1e6)  # Output: 12.27
```

---

### C-A2: Kompatibilitas Platform (CPU-only capable)

**Requirement:** Model wajib tetap dapat berjalan di lingkungan CPU-only.

**Implementasi:**

Seluruh pipeline inferensi pada `inference.ipynb` menggunakan ONNX
Runtime dengan `CPUExecutionProvider` secara eksplisit. Tidak ada
dependensi terhadap CUDA, cuDNN, atau akselerasi GPU apapun dalam kode
inferensi.

```python
# inference.ipynb — inisialisasi session
session = ort.InferenceSession(
    str(MODEL_PATH),
    providers=['CPUExecutionProvider']  # CPU only, no GPU
)
```

Pemisahan antara environment pelatihan (GPU) dan inferensi (CPU) dilakukan
secara arsitektural: pelatihan menggunakan PyTorch dengan `device='cuda'`,
sedangkan inferensi sepenuhnya menggunakan ONNX Runtime CPU. Format ONNX
dipilih justru karena portabilitasnya — model dapat dijalankan pada mesin
apapun yang memiliki Python dan `onnxruntime` tanpa dependensi CUDA.

**Verifikasi:**
```
Provider aktif: ['CPUExecutionProvider']
# Dikonfirmasi dari output inference.ipynb
```

---

### C-A3: Kecepatan Inferensi ≤ 3.000 ms per Sampel (CPU, i5 Gen 8+)

**Requirement:** Waktu inferensi per satu sampel input tidak boleh melebihi
3 detik pada mesin CPU standar (minimum Intel Core i5 Gen 8 / setara).
Pengukuran dilakukan pada kondisi CPU tanpa akselerasi GPU.

**Implementasi:**

Beberapa keputusan desain dibuat secara spesifik untuk memenuhi constraint
ini:

| Keputusan Desain | Nilai | Dampak terhadap Latensi |
|---|---|---|
| Arsitektur | YOLOv8n (nano) | ~8x lebih cepat dari YOLOv8m |
| Resolusi input | 640 × 640 px | Standar optimal accuracy/speed |
| Format inferensi | ONNX Runtime | Lebih cepat dari PyTorch CPU mode |
| Simplifikasi graf | `simplify=True` | Mengurangi overhead komputasi |
| Input shape | Fixed (non-dynamic) | Waktu inferensi deterministik |

**Hasil benchmark CPU** (dijalankan pada Intel Core i5-12400F,
`CPUExecutionProvider`, 30 sampel dari `test_data/`):

| Metrik | Nilai | Batas Constraint | Status |
|---|---|---|---|
| Latensi rata-rata | 29.0 ms | — | — |
| Latensi P95 | 31.8 ms | — | — |
| Latensi maksimum | **31.9 ms** | **3.000 ms** | **PASS ✓** |

Latensi maksimum 31.9 ms berada **98.9% di bawah batas constraint**,
memberikan margin 2.968 ms. Bahkan pada prosesor i5 Gen 8 yang secara
*single-thread performance* lebih lambat ~2.5× dari i5-12400F, estimasi
latensi maksimum adalah ~80 ms — masih jauh di bawah 3.000 ms.

Laporan benchmark lengkap tersedia di `docs/cpu_benchmark.txt`.

---

### C-A4: Framework

**Requirement:** Model wajib menggunakan salah satu framework berikut:
PyTorch, TensorFlow/Keras, atau ONNX Runtime.

**Implementasi:**

Sistem menggunakan dua framework yang keduanya tercantum dalam constraint:

| Tahap | Framework | Versi |
|---|---|---|
| Pelatihan | **PyTorch** via Ultralytics | torch 2.5.1+cu121 |
| Inferensi | **ONNX Runtime** | onnxruntime 1.23.2 |

Alur PyTorch → ONNX → ONNX Runtime merupakan workflow deployment standar
yang direkomendasikan secara resmi dan sepenuhnya memenuhi constraint
framework. Tidak ada framework di luar daftar yang digunakan sebagai
komponen inti sistem.

---

### C-A5: Offline Total

**Requirement:** Seluruh proses inferensi berjalan secara offline
(localhost). Dilarang menggunakan API eksternal atau cloud inference dalam
pipeline inferensi.

**Implementasi:**

Sistem RescueVision Edge dirancang dari awal dengan prinsip *sovereign AI*
— seluruh komputasi berjalan lokal tanpa ketergantungan jaringan. Audit
dependensi `inference.ipynb` mengkonfirmasi tidak ada library atau panggilan
jaringan eksternal:

```
Dependensi inference.ipynb:
  onnxruntime     ← inferensi lokal
  numpy           ← komputasi numerik
  opencv-python   ← pemrosesan citra lokal
  matplotlib      ← visualisasi lokal
  pathlib         ← operasi file lokal

Tidak ada:
  ✗ requests / urllib (HTTP calls)
  ✗ google-cloud-vision
  ✗ boto3 (AWS)
  ✗ openai
  ✗ huggingface_hub inference API
  ✗ koneksi jaringan apapun
```

Model dimuat dari file lokal `model.onnx` pada setiap sesi inferensi.
Sistem dapat beroperasi penuh tanpa koneksi internet, sesuai dengan
skenario penggunaan di area bencana yang seringkali mengalami gangguan
infrastruktur jaringan.

---

## 3.2 Constraint Umum

### CU-1: Struktur File

**Requirement:** Wajib mengumpulkan proposal.pdf, training.ipynb (dengan
log terlihat), inference.ipynb (script bersih), file model, folder
train_data, dan folder test_data secara terpisah.

**Status pengumpulan:**

| File/Folder | Status | Keterangan |
|---|---|---|
| `proposal.pdf` | ✓ | Dokumen ini |
| `training.ipynb` | ✓ | Log epoch 1–100 visible |
| `inference.ipynb` | ✓ | Script bersih, siap dijalankan |
| `model.onnx` | ✓ | 12.27 MB, ONNX opset 12 |
| `train_data/` | ✓ | 5.655 train + 530 val images & labels |
| `test_data/` | ✓ | 1.265 images & labels, terpisah |

### CU-2: Reproducibility

Model dapat dilatih ulang sepenuhnya dari `training.ipynb` dengan dataset
yang sama. Seluruh hyperparameter tercatat di sel konfigurasi notebook.
`seed=0` digunakan untuk determinisme. Inferensi dapat dijalankan di
lingkungan CPU-only tanpa GPU.

### CU-3: Bahasa Kode

Seluruh kode ditulis dalam **Python 3.10** menggunakan library standar
(*PyTorch, Ultralytics, ONNX Runtime, OpenCV, NumPy*). Tidak ada komponen
dalam bahasa lain.

### CU-4: Larangan Cloud Inference

Tidak ada API inferensi cloud yang digunakan dalam pipeline utama. Lihat
C-A5 untuk audit lengkap.

### CU-5: Proposal Bab 3

Bab ini merupakan pemenuhan requirement CU-5 — dedikasi satu bab penuh
untuk menjelaskan kepatuhan terhadap setiap poin constraint track.

---

## 3.3 Ringkasan Kepatuhan

| Constraint | Requirement | Hasil | Status |
|---|---|---|---|
| C-A1 | ≤ 50 MB | 12.27 MB | **PASS ✓** |
| C-A2 | CPU-only capable | CPUExecutionProvider | **PASS ✓** |
| C-A3 | ≤ 3.000 ms (CPU) | 31.9 ms maks | **PASS ✓** |
| C-A4 | PyTorch/TF/ONNX | PyTorch + ONNX Runtime | **PASS ✓** |
| C-A5 | Offline total | Zero external calls | **PASS ✓** |
| CU-1 | Struktur file lengkap | Semua file tersedia | **PASS ✓** |
| CU-2 | Reproducible | Seed=0, config terdokumentasi | **PASS ✓** |
| CU-3 | Python utama | Python 3.10 (100%) | **PASS ✓** |
| CU-4 | No cloud inference | Zero API calls | **PASS ✓** |

Seluruh constraint wajib terpenuhi dengan margin yang signifikan,
khususnya pada C-A1 (model 75% lebih kecil dari batas) dan C-A3
(inferensi 98.9% lebih cepat dari batas).
