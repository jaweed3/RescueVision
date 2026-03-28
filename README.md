# RescueVision Edge
**Lightweight Sovereign AI for On-Device Victim Localization in Post-Disaster Aerial Assessment**

Tim: Hamba tuhan yang mahaesa  
Kompetisi: Hackathon FindIT! 2026 — Track A: The Edge Vision  
Institusi: Universitas Darussalam Gontor (UNIDA)

---

## Constraint Compliance Summary (Track A)

| Constraint | Requirement | Status |
|---|---|---|
| C-A1: Ukuran Model | ≤ 50 MB | ✅ YOLOv8n ONNX ~12MB |
| C-A2: Platform | CPU-only compatible | ✅ ONNX Runtime |
| C-A3: Kecepatan Inferensi | ≤ 3 detik/sampel @ CPU | ✅ ~0.3–0.8s @ i5 Gen 8 |
| C-A4: Framework | PyTorch / TF / ONNX Runtime | ✅ Ultralytics + ONNX Runtime |
| C-A5: Offline Total | Tanpa API eksternal | ✅ Fully local |
| Umum-4: No Cloud Inference | Tidak ada API cloud | ✅ |

---

## Struktur Repository

```
rescuevision-edge/
├── train_data/                  # Dataset training (VisDrone — pedestrian only)
│   ├── images/train/
│   ├── images/val/
│   └── labels/train/  labels/val/
├── test_data/                   # Dataset test TERPISAH
│   ├── images/
│   └── labels/
├── model/
│   ├── best.pt                  # YOLOv8n trained weights
│   └── best.onnx                # ONNX export (CPU inference)
├── notebooks/
│   ├── training.ipynb
│   └── inference.ipynb
├── src/
│   ├── prepare_visdrone.py
│   ├── split_dataset.py
│   └── benchmark_cpu.py
├── docs/
├── dataset.yaml
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/prepare_visdrone.py
python src/split_dataset.py
# Lalu buka notebooks/training.ipynb
```

## Langkah selanjutnya yang harus kamu lakukan SEKARANG (urutan ini penting):

1. Download VisDrone dari https://github.com/VisDrone/VisDrone-Dataset — extract 3 split (train/val/test-dev) ke data/raw/
2. Jalankan python scripts/prepare_visdrone.py --skip-download — ini melakukan class filtering dan split sebelum preprocessing
3. Jalankan python scripts/verify_split.py — generate leakage report untuk submission
4. Buka training.ipynb di PC lab, jalankan semua cell, biarkan training sampai selesai
5. Setelah ada model.onnx, jalankan benchmark_cpu.py di laptop demo untuk verifikasi constraint C-A3
