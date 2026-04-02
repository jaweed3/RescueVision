# RescueVision Edge

**Lightweight Sovereign AI for On-Device Victim Localization in Post-Disaster Aerial Assessment**

> Hackathon FindIT! 2026 — Track A: The Edge Vision (Computer Vision)  
> Universitas Darussalam Gontor (UNIDA) — Tim _Hamba tuhan yang mahaesa_

---

## Ringkasan

RescueVision Edge adalah sistem deteksi korban bencana dari citra udara _drone_ yang berjalan sepenuhnya secara luring (_offline_), tanpa ketergantungan pada _cloud computing_ atau API eksternal apapun. Sistem menggunakan YOLOv8n yang dioptimasi dan diekspor ke format ONNX untuk inferensi CPU-only dengan latensi <40ms per citra.

**Hasil utama:**

| Metrik                                 | Nilai    |
| -------------------------------------- | -------- |
| mAP@0.5 (VisDrone pedestrian)          | 0.5280   |
| mAP@0.5:0.95                           | 0.2159   |
| Ukuran model (ONNX)                    | 11.70 MB |
| Latensi inferensi CPU (max, 30 sampel) | 38.1 ms  |
| Baseline YOLOv5n mAP@0.5               | 0.4684   |

---

## Kepatuhan Constraint Track A

| Constraint         | Requirement            | Implementasi               | Status  |
| ------------------ | ---------------------- | -------------------------- | ------- |
| C-A1 Ukuran Model  | ≤ 50 MB                | ONNX 11.70 MB              | ✅ PASS |
| C-A2 Platform      | CPU-only capable       | `CPUExecutionProvider`     | ✅ PASS |
| C-A3 Kecepatan     | ≤ 3.000 ms/sampel      | 38.1 ms max                | ✅ PASS |
| C-A4 Framework     | PyTorch / ONNX Runtime | Ultralytics + ONNX Runtime | ✅ PASS |
| C-A5 Offline Total | Tanpa API eksternal    | Zero external calls        | ✅ PASS |

---

## Struktur Repository

```
RescueVision/
│
├── notebooks/
│   ├── training.ipynb               # Pipeline training lengkap + log visible
│   └── inference.ipynb              # Script inferensi bersih, CPU-only
│
├── model/
│   ├── best.pt                      # YOLOv8n trained weights (PyTorch)
│   └── best.onnx                    # Model final untuk inferensi (ONNX)
│
├── train_data/                      # Dataset training + validasi
│   ├── images/train/                # 5.655 gambar
│   ├── images/val/                  # 530 gambar
│   └── labels/train/  labels/val/
│
├── test_data/                       # Dataset test (dipisah sebelum preprocessing)
│   ├── images/                      # 1.265 gambar
│   └── labels/
│
├── runs/                            # Output training Ultralytics
│   ├── detect/runs/train/
│   │   └── rescuevision_v13/        # YOLOv8n final (100 epoch, mAP50=0.528)
│   └── yolov5n_baseline/            # YOLOv5n baseline experiment
│
├── scripts/
│   ├── prepare_visdrone.py          # Filter kelas + konversi YOLO format
│   ├── verify_split.py              # Verifikasi zero data leakage
│   └── benchmark_cpu.py             # Benchmark latensi inferensi CPU
│
├── backend/                         # FastAPI backend (Tahap 3)
├── frontend/                        # React + Vite frontend (Tahap 3)
├── docs/                            # Dokumentasi + laporan constraint
├── dataset.yaml                     # Konfigurasi dataset Ultralytics
├── requirements.txt
└── README.md
```

---

## Setup Environment

```bash
# Aktifkan conda environment
conda activate mlenv

# Install dependensi
pip install -r requirements.txt

# Download VisDrone dataset (manual)
# https://github.com/VisDrone/VisDrone-Dataset
# Extract ke: data/raw/
# Struktur yang dibutuhkan:
#   data/raw/VisDrone2019-DET-train/images/ & annotations/
#   data/raw/VisDrone2019-DET-val/images/ & annotations/
#   data/raw/VisDrone2019-DET-test-dev/images/ & annotations/

# Siapkan dataset
python scripts/prepare_visdrone.py --skip-download

# Verifikasi zero data leakage
python scripts/verify_split.py
```

---

## Training

Buka `notebooks/training.ipynb` dan jalankan semua sel secara berurutan.

**Konfigurasi utama:**

```python
model   = 'yolov8n.pt'   # YOLOv8 nano — 3.2M parameter
imgsz   = 640
batch   = 16
epochs  = 100             # early stopping patience=20
device  = 0               # NVIDIA GeForce RTX 4060
```

---

## Inferensi

Buka `notebooks/inference.ipynb` dan jalankan semua sel.

- Model dimuat dari `model/best.onnx`
- Inferensi menggunakan `CPUExecutionProvider` — tanpa GPU
- Output: _bounding box_, _confidence score_, koordinat relatif korban

```
Contoh output:
  Inference time : 41.5 ms  (limit: 3000 ms)
  Detections     : 3 pedestrian(s)
  ✅ Constraint C-A3 PASS

  [1] (1040.6, 161.2, 1048.6, 175.1) conf=0.460
  [2] ( 865.3, 155.4,  871.8, 170.5) conf=0.440
  [3] (1134.8, 161.1, 1141.3, 174.8) conf=0.437
```

---

## Benchmark CPU

```bash
python scripts/benchmark_cpu.py --model model/best.onnx --images test_data/images/ --n 30
```

Laporan tersimpan di `docs/cpu_benchmark.txt`.

---

## Dataset

**VisDrone-DET 2019** — Task 1: Object Detection in Images  
Sumber: https://github.com/VisDrone/VisDrone-Dataset

| Split | Gambar | Lokasi                     |
| ----- | ------ | -------------------------- |
| Train | 5.655  | `train_data/images/train/` |
| Val   | 530    | `train_data/images/val/`   |
| Test  | 1.265  | `test_data/images/`        |

Hanya kelas **pedestrian** (1) dan **people** (2) yang digunakan, digabung menjadi satu kelas `pedestrian`. Pemisahan `test_data/` dilakukan **sebelum** preprocessing apapun. Laporan verifikasi leakage: `docs/leakage_report.txt`.

---

## Perbandingan Arsitektur

| Metrik             | YOLOv5n (baseline) | YOLOv8n (final) |
| ------------------ | ------------------ | --------------- |
| mAP@0.5            | 0.4684             | **0.5280**      |
| mAP@0.5:0.95       | 0.1728             | **0.2159**      |
| ONNX size          | 7.49 MB            | 11.70 MB        |
| CPU latency (mean) | 18.0 ms            | 30.4 ms         |
| CPU latency (max)  | 19.8 ms            | 38.1 ms         |

YOLOv8n dipilih karena unggul 5.96 poin mAP@0.5 dengan latensi CPU tetap jauh di bawah batas 3.000 ms. Lihat `docs/architecture_comparison.txt` untuk laporan lengkap.

---

## Tim

| Nama                    | NIM          | 
| ----------------------- | ------------ |
| Wafa Bila Syaefurokhman | 442023611098 |
| Farrel Ghozy Affifudin  | 452024611053 |
| Fatih Jawwad Al Mumtaz  | 452024611047 |
| Sabri Mutiur Rahman     | 442023611104 |

---

## Lisensi

Dataset VisDrone-DET 2019 digunakan untuk keperluan penelitian dan kompetisi non-komersial sesuai ketentuan distribusi resmi. Model YOLOv8n menggunakan lisensi AGPL-3.0 dari Ultralytics.
